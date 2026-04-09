#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de chat contextual para análisis de imágenes.
Permite hacer preguntas sobre imágenes ya analizadas usando YOLO + GPT-4 Vision.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import OpenAI
from src.utils.config import get_llm_config

logger = logging.getLogger(__name__)

class ChatService:
    """
    Servicio que maneja conversaciones contextuales sobre imágenes analizadas.
    Combina información de YOLO y GPT-4 Vision para responder preguntas específicas.
    """

    MAX_SESSIONS = 50
    SESSION_TTL_HOURS = 2

    def __init__(self):
        """Inicializa el servicio de chat."""
        llm_config = get_llm_config()
        self.provider = llm_config["provider"]
        self.config = llm_config["config"]
        self.client = self._setup_client()
        self.context_storage = {}
        logger.info("Servicio de chat contextual inicializado con provider: %s", self.provider)

    def _setup_client(self) -> Optional[OpenAI]:
        """Configura el cliente segun el proveedor."""
        if self.provider == "groq":
            vision_model = self.config.get("vision_model", "meta-llama/llama-4-scout-17b-16e-instruct")
            self.config["model"] = vision_model
            return OpenAI(base_url=self.config["base_url"], api_key=self.config["api_key"])
        elif self.provider == "openai":
            api_key = self.config.get("api_key")
            if api_key:
                return OpenAI(api_key=api_key)
        elif self.provider == "docker":
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                from src.utils.config import get_openai_config
                self.config = get_openai_config()
                return OpenAI(api_key=api_key)
        logger.warning("Chat contextual no disponible para provider: %s", self.provider)
        return None

    def store_analysis_context(self, session_id: str, analysis_results: Dict[str, Any],
                             yolo_results: Dict[str, Any], image_filename: str,
                             encoded_image: Optional[str] = None, image_format: str = "jpeg") -> None:
        """
        Almacena el contexto de un análisis para futuras consultas.
        
        Args:
            session_id: ID único de la sesión
            analysis_results: Resultados del análisis geográfico
            yolo_results: Resultados de detección YOLO
            image_filename: Nombre del archivo de imagen
            encoded_image: Imagen codificada en base64 para análisis visual específico
            image_format: Formato de la imagen (jpeg, png, etc.)
        """
        self._cleanup_expired_sessions()
        self.context_storage[session_id] = {
            "timestamp": datetime.now().isoformat(),
            "image_filename": image_filename,
            "geographic_analysis": analysis_results,
            "yolo_detection": yolo_results,
            "encoded_image": encoded_image,
            "image_format": image_format,
            "chat_history": []
        }
        logger.info(f"Contexto almacenado para sesión: {session_id}")

    def _cleanup_expired_sessions(self) -> None:
        """Elimina sesiones expiradas y limita el total."""
        now = datetime.now()
        expired = [
            sid for sid, data in self.context_storage.items()
            if (now - datetime.fromisoformat(data["timestamp"])).total_seconds() > self.SESSION_TTL_HOURS * 3600
        ]
        for sid in expired:
            del self.context_storage[sid]

        # Si aun hay demasiadas, eliminar las mas antiguas
        if len(self.context_storage) >= self.MAX_SESSIONS:
            sorted_sessions = sorted(
                self.context_storage.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for sid, _ in sorted_sessions[:len(self.context_storage) - self.MAX_SESSIONS + 1]:
                del self.context_storage[sid]

    def ask_question(self, session_id: str, question: str) -> Dict[str, Any]:
        """
        Procesa una pregunta sobre la imagen analizada.
        
        Args:
            session_id: ID de la sesión
            question: Pregunta del usuario
            
        Returns:
            Respuesta del chat con contexto
        """
        try:
            # Verificar si existe contexto para esta sesión
            if session_id not in self.context_storage:
                return {
                    "error": "No hay contexto de análisis disponible para esta sesión",
                    "response": "Por favor, analiza una imagen primero antes de hacer preguntas.",
                    "status": "error"
                }
            
            context = self.context_storage[session_id]
            
            # Detectar si es una pregunta visual específica
            if self._is_visual_question(question) and context.get("encoded_image"):
                logger.info(f"Pregunta visual detectada: {question}")
                return self._handle_visual_question(session_id, question, context)
            
            # Construir prompt contextual para preguntas estándar
            system_prompt = self._build_chat_system_prompt(context)
            user_prompt = self._build_chat_user_prompt(question, context)
            
            # Crear conversación con historial
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Agregar historial de chat
            for chat_entry in context["chat_history"]:
                messages.append({"role": "user", "content": chat_entry["question"]})
                messages.append({"role": "assistant", "content": chat_entry["response"]})
            
            # Agregar pregunta actual
            messages.append({"role": "user", "content": user_prompt})
            
            # Obtener respuesta de GPT-4
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,  # type: ignore
                temperature=0.3,
                max_tokens=1000,
            )
            
            # Extraer respuesta
            answer = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            
            # Guardar en historial
            context["chat_history"].append({
                "question": question,
                "response": answer,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "response": answer,
                "question": question,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error en chat contextual: {str(e)}")
            return {
                "error": str(e),
                "response": "Lo siento, ocurrió un error al procesar tu pregunta.",
                "status": "error"
            }
    
    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de chat para una sesión.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Lista del historial de chat
        """
        if session_id not in self.context_storage:
            return []
        
        return self.context_storage[session_id]["chat_history"]
    
    def clear_chat_history(self, session_id: str) -> bool:
        """
        Limpia el historial de chat para una sesión.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            True si se limpió exitosamente
        """
        if session_id in self.context_storage:
            self.context_storage[session_id]["chat_history"] = []
            return True
        return False
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Obtiene un resumen del contexto de análisis.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Resumen del contexto
        """
        if session_id not in self.context_storage:
            return {"error": "No hay contexto disponible"}
        
        context = self.context_storage[session_id]
        geo_analysis = context["geographic_analysis"]
        yolo_detection = context["yolo_detection"]
        
        return {
            "image_filename": context["image_filename"],
            "timestamp": context["timestamp"],
            "geographic_results": {
                "country": geo_analysis.get("country", "No determinado"),
                "city": geo_analysis.get("city", "No determinado"),
                "confidence": geo_analysis.get("confidence", 0)
            },
            "yolo_results": {
                "total_objects": yolo_detection.get("total_objects", 0),
                "categories": len(yolo_detection.get("object_summary", {})),
                "top_objects": list(yolo_detection.get("object_summary", {}).keys())[:5]
            },
            "chat_messages": len(context["chat_history"])
        }
    
    def _build_chat_system_prompt(self, context: Dict[str, Any]) -> str:
        """Construye el prompt de sistema para el chat."""
        geo_analysis = context["geographic_analysis"]
        yolo_detection = context["yolo_detection"]
        
        return f"""
        Eres un asistente especializado en análisis de imágenes que puede responder preguntas 
        sobre una imagen que ya fue analizada usando YOLO 11 para detección de objetos y 
        GPT-4 Vision para análisis geográfico.
        
        CONTEXTO DE LA IMAGEN ANALIZADA:
        - Archivo: {context["image_filename"]}
        - Fecha de análisis: {context["timestamp"]}
        
        RESULTADOS DEL ANÁLISIS GEOGRÁFICO:
        - País: {geo_analysis.get("country", "No determinado")}
        - Ciudad: {geo_analysis.get("city", "No determinado")}
        - Distrito: {geo_analysis.get("district", "No determinado")}
        - Confianza: {geo_analysis.get("confidence", 0)}%
        - Evidencia: {', '.join(geo_analysis.get("supporting_evidence", []))}
        
        RESULTADOS DE DETECCIÓN DE OBJETOS (YOLO 11):
        - Total de objetos: {yolo_detection.get("total_objects", 0)}
        - Objetos detectados: {json.dumps(yolo_detection.get("object_summary", {}), indent=2)}
        - Objetos prominentes: {json.dumps(yolo_detection.get("prominent_objects", []), indent=2)}
        - Indicadores geográficos: {json.dumps(yolo_detection.get("geographic_indicators", {}), indent=2)}
        
        INSTRUCCIONES:
        1. Responde preguntas específicas sobre la imagen usando esta información
        2. Combina datos de YOLO y análisis geográfico cuando sea relevante
        3. Sé preciso con números y detalles técnicos
        4. Explica cómo llegaste a tus conclusiones
        5. Si no tienes la información específica, di que no la tienes
        6. Mantén las respuestas concisas pero informativas
        7. Usa emojis apropiados para hacer las respuestas más amigables
        
        Puedes responder preguntas sobre:
        - Objetos detectados (tipos, cantidades, ubicaciones)
        - Análisis geográfico (por qué se determinó cierta ubicación)
        - Comparaciones entre diferentes elementos
        - Detalles técnicos del análisis
        - Confianza en los resultados
        """
    
    def _build_chat_user_prompt(self, question: str, context: Dict[str, Any]) -> str:
        """Construye el prompt del usuario para el chat."""
        return f"""
        Pregunta sobre la imagen "{context["image_filename"]}":
        
        {question}
        
        Por favor responde usando toda la información disponible del análisis.
        """
    
    def get_suggested_questions(self, session_id: str) -> List[str]:
        """
        Genera preguntas sugeridas basadas en el contexto.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Lista de preguntas sugeridas
        """
        if session_id not in self.context_storage:
            return []
        
        context = self.context_storage[session_id]
        yolo_detection = context["yolo_detection"]
        geo_analysis = context["geographic_analysis"]
        
        suggestions = []
        
        # Preguntas sobre objetos detectados
        if yolo_detection.get("total_objects", 0) > 0:
            suggestions.append(f"¿Cuántos objetos detectó YOLO exactamente?")
            
            top_objects = list(yolo_detection.get("object_summary", {}).keys())
            if top_objects:
                suggestions.append(f"¿Puedes describir los {top_objects[0]} que detectaste?")
        
        # Preguntas sobre análisis geográfico
        if geo_analysis.get("confidence", 0) > 0:
            suggestions.append(f"¿Cómo determinaste que era {geo_analysis.get('country', 'este país')}?")
            suggestions.append(f"¿Qué nivel de confianza tienes en el análisis?")
        
        # Preguntas visuales específicas (solo si hay imagen codificada)
        if context.get("encoded_image"):
            top_objects = list(yolo_detection.get("object_summary", {}).keys())
            if top_objects:
                # Preguntas sobre colores de objetos específicos
                suggestions.append(f"¿De qué color son los {top_objects[0]} en la imagen?")
                suggestions.append(f"¿Cómo es el aspecto de los {top_objects[0]}?")
            
            # Preguntas visuales generales
            suggestions.append("¿Qué colores predominan en la imagen?")
            suggestions.append("¿Puedes describir el estado de los objetos visibles?")
        
        # Preguntas sobre la combinación
        suggestions.append("¿Cómo te ayudó YOLO a mejorar el análisis geográfico?")
        suggestions.append("¿Qué elementos fueron más importantes para la identificación?")
        
        return suggestions[:6]  # Máximo 6 sugerencias
    
    def _is_visual_question(self, question: str) -> bool:
        """
        Detecta si una pregunta requiere análisis visual específico.
        
        Args:
            question: Pregunta del usuario
            
        Returns:
            True si requiere análisis visual específico
        """
        visual_keywords = [
            # Colores
            'color', 'colores', 'qué color', 'de qué color', 'rojo', 'azul', 'verde', 
            'amarillo', 'negro', 'blanco', 'gris', 'naranja', 'rosa', 'morado', 'violeta',
            
            # Formas y características físicas
            'forma', 'formas', 'aspecto', 'apariencia', 'tamaño', 'grande', 'pequeño',
            'alto', 'bajo', 'ancho', 'estrecho', 'redondo', 'cuadrado', 'rectangular',
            
            # Detalles específicos
            'detalle', 'detalles', 'específico', 'exacto', 'preciso', 'describe',
            'cómo se ve', 'cómo es', 'qué tal', 'marca', 'modelo', 'tipo',
            
            # Características visuales
            'brillo', 'luminoso', 'oscuro', 'claro', 'opaco', 'transparente',
            'textura', 'superficie', 'material', 'acabado', 'estado',
            
            # Patrones y elementos
            'patrón', 'diseño', 'estilo', 'rayado', 'liso', 'rugoso',
            'nuevo', 'viejo', 'antiguo', 'moderno', 'deteriorado'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in visual_keywords)
    
    def _handle_visual_question(self, session_id: str, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja preguntas que requieren análisis visual específico.
        
        Args:
            session_id: ID de la sesión
            question: Pregunta del usuario
            context: Contexto de la sesión
            
        Returns:
            Respuesta del análisis visual específico
        """
        try:
            # Construir prompt para análisis visual específico
            visual_prompt = self._build_visual_analysis_prompt(question, context)
            
            # Crear mensaje para GPT-4 Vision
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": visual_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{context['image_format']};base64,{context['encoded_image']}"
                            }
                        }
                    ]
                }
            ]
            
            # Llamar a GPT-4 Vision para análisis específico
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,  # type: ignore
                temperature=0.3,
                max_tokens=1000,
            )
            
            # Extraer respuesta
            answer = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            
            # Agregar información contextual
            enhanced_answer = self._enhance_visual_response(answer, context)
            
            # Guardar en historial
            context["chat_history"].append({
                "question": question,
                "response": enhanced_answer,
                "timestamp": datetime.now().isoformat(),
                "type": "visual_analysis"
            })
            
            return {
                "response": enhanced_answer,
                "question": question,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "analysis_type": "visual_specific"
            }
            
        except Exception as e:
            logger.error(f"Error en análisis visual específico: {str(e)}")
            return {
                "error": str(e),
                "response": "Lo siento, no pude analizar los detalles visuales específicos de la imagen.",
                "status": "error"
            }
    
    def _build_visual_analysis_prompt(self, question: str, context: Dict[str, Any]) -> str:
        """
        Construye un prompt específico para análisis visual.
        
        Args:
            question: Pregunta del usuario
            context: Contexto de la sesión
            
        Returns:
            Prompt para análisis visual específico
        """
        geo_analysis = context["geographic_analysis"]
        yolo_detection = context["yolo_detection"]
        
        return f"""
        Eres un especialista en análisis visual de imágenes. Analiza esta imagen con detalle para responder la siguiente pregunta específica sobre características visuales.

        PREGUNTA ESPECÍFICA: {question}

        CONTEXTO DE LA IMAGEN:
        - Archivo: {context["image_filename"]}
        - Ubicación identificada: {geo_analysis.get("country", "No determinado")}, {geo_analysis.get("city", "No determinado")}
        - Objetos detectados por YOLO: {json.dumps(yolo_detection.get("object_summary", {}), indent=2)}

        INSTRUCCIONES PARA ANÁLISIS VISUAL:
        1. Observa cuidadosamente la imagen para identificar características visuales específicas
        2. Enfócate en colores, formas, texturas, materiales, estado y detalles específicos
        3. Proporciona descripciones precisas y detalladas
        4. Si identificas marcas, modelos o características específicas, menciónalas
        5. Combina tu análisis visual con el contexto geográfico conocido
        6. Sé específico con colores (no solo "azul", sino "azul oscuro", "azul cielo", etc.)
        7. Describe el estado de los objetos (nuevo, usado, deteriorado, etc.)
        8. Menciona cualquier detalle que sea relevante para la pregunta

        IMPORTANTE:
        - Responde únicamente basándote en lo que puedes ver claramente en la imagen
        - Si no puedes determinar algo con certeza, dilo claramente
        - Proporciona detalles específicos y precisos
        - Usa terminología técnica apropiada cuando sea relevante

        Responde la pregunta con el máximo detalle visual posible.
        """
    
    def _enhance_visual_response(self, visual_response: str, context: Dict[str, Any]) -> str:
        """
        Mejora la respuesta visual con información contextual.
        
        Args:
            visual_response: Respuesta del análisis visual
            context: Contexto de la sesión
            
        Returns:
            Respuesta mejorada con contexto
        """
        geo_analysis = context["geographic_analysis"]
        
        enhanced_response = f"""
        {visual_response}

        🔍 **Análisis Visual Específico Completado**

        Esta información se basa en:
        • **Análisis visual directo** de la imagen usando GPT-4 Vision
        • **Contexto geográfico**: {geo_analysis.get('country', 'No determinado')}, {geo_analysis.get('city', 'No determinado')}
        • **Objetos detectados**: {context['yolo_detection'].get('total_objects', 0)} objetos identificados

        💡 *Tip*: Puedes hacer más preguntas específicas sobre colores, formas o características visuales de cualquier elemento en la imagen.
        """
        
        return enhanced_response.strip()