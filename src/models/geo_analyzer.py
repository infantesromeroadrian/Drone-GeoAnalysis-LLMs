#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo que implementa el modelo de análisis geográfico de imágenes.
"""

import logging
import json
import re
from openai import OpenAI
from openai.types.chat import ChatCompletion
from typing import Dict, Any, List, Optional

from src.utils.config import get_llm_config

logger = logging.getLogger(__name__)

class GeoAnalyzer:
    """
    Clase que implementa la lógica para analizar imágenes y determinar
    su ubicación geográfica usando LLM con análisis de visión.
    """
    
    def __init__(self):
        """Inicializa el analizador geográfico."""
        self.llm_config = get_llm_config()
        self.provider = self.llm_config["provider"]
        self.config = self.llm_config["config"]
        
        # Configurar cliente según proveedor
        self._setup_client()
        
        logger.info(f"Analizador geográfico inicializado con proveedor: {self.provider}")
    
    def _setup_client(self) -> None:
        """Configura el cliente LLM según el proveedor."""
        if self.provider == "docker":
            logger.warning("Docker Models no soporta analisis de imagenes. Intentando OpenAI como fallback.")
            self._setup_openai_fallback()
        elif self.provider == "openai":
            logger.info("Inicializando OpenAI API para análisis de imágenes")
            self.client = OpenAI(api_key=self.config["api_key"])
        elif self.provider == "groq":
            logger.info("Inicializando Groq API para analisis de imagenes con vision")
            self.client = OpenAI(
                base_url=self.config["base_url"],
                api_key=self.config["api_key"]
            )
            self.config["model"] = self.config.get("vision_model", "meta-llama/llama-4-scout-17b-16e-instruct")
        else:
            self.client = None
            logger.warning("Proveedor LLM no soportado para vision: %s", self.provider)

    def _setup_openai_fallback(self) -> None:
        """Configura OpenAI como fallback para análisis de imágenes."""
        import os
        from src.utils.config import get_openai_config
        self.config = get_openai_config()
        api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.client = None
            logger.warning("OPENAI_API_KEY no disponible. Analisis de imagenes deshabilitado.")
            return
        self.client = OpenAI(api_key=api_key)
        self.provider = "openai"
        
    def analyze_image(self, base64_image: str, metadata: Dict[str, Any], image_format: str = 'jpeg') -> Dict[str, Any]:
        """
        Analiza una imagen para detectar su ubicación geográfica.
        
        Args:
            base64_image: Imagen codificada en base64
            metadata: Metadatos de la imagen
            image_format: Formato de la imagen ('jpeg', 'png', 'gif', 'webp')
            
        Returns:
            Diccionario con los resultados del análisis
        """
        logger.info(f"Analizando imagen: {metadata.get('filename', 'unknown')} con {self.provider}")
        
        # Validar configuración de API
        api_validation = self._validate_api_configuration()
        if "error" in api_validation:
            return api_validation
        
        try:
            # Crear solicitud a la API
            response = self._create_vision_request(base64_image, metadata, image_format)
            
            # Procesar respuesta
            result = self._process_response(response)
            logger.info(f"Análisis completado con éxito usando {self.provider}")
            return result
            
        except Exception as e:
            logger.error(f"Error en el análisis con {self.provider}: {str(e)}")
            return self._create_error_response(str(e))
    
    def _validate_api_configuration(self) -> Dict[str, Any]:
        """Valida la configuración de la API."""
        if self.client is None or not self.config.get("api_key") or self.config["api_key"].startswith("your_"):
            logger.error("API key no configurada o cliente de vision no disponible")
            return {
                "error": f"API key no configurada para {self.provider}. El analisis de imagenes requiere un provider con soporte vision.",
                "country": "No configurado",
                "city": "No configurado", 
                "district": "No configurado",
                "neighborhood": "No configurado",
                "street": "No configurado",
                "confidence": 0,
                "supporting_evidence": ["API key de OpenAI requerida para análisis de imágenes"]
            }
        return {"valid": True}
        
    def _create_vision_request(self, base64_image: str, metadata: Dict[str, Any], image_format: str):
        """Crea la solicitud a la API de visión."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(metadata)
        
        return self.client.chat.completions.create(
            model=self.config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", 
                     "image_url": {"url": f"data:image/{image_format};base64,{base64_image}"}}
                ]}
            ],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
        )
            
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Crea una respuesta de error estandarizada."""
        return {
            "error": error_message,
            "country": "Error",
            "city": "Error",
            "district": "Error",
            "neighborhood": "Error",
            "street": "Error",
            "confidence": 0,
            "supporting_evidence": [f"Error con {self.provider}: {error_message}"]
        }
    
    def _build_system_prompt(self) -> str:
        """Construye el prompt de sistema para la API."""
        return self._get_osint_analysis_instructions()
        
    def _get_osint_analysis_instructions(self) -> str:
        """Obtiene las instrucciones de análisis OSINT."""
        return """
        Eres un sistema avanzado de análisis de inteligencia visual OSINT especializado en 
        identificación geográfica. Tu tarea es analizar la imagen proporcionada y determinar 
        con la mayor precisión posible la ubicación geográfica donde fue tomada.
        
        Debes analizar cuidadosamente los siguientes elementos:
        1. Arquitectura y estilo de los edificios
        2. Señalización, carteles y texto visible
        3. Vegetación y paisaje natural
        4. Personas, vestimenta y características culturales
        5. Vehículos y sistemas de transporte
        6. Estructura urbana y organización de calles
        7. Monumentos o puntos de referencia
        8. Cualquier otro elemento distintivo
        
        Para cada identificación, proporciona:
        - País: Nombre del país
        - Ciudad: Nombre de la ciudad
        - Distrito: Área administrativa mayor
        - Barrio: Vecindario específico
        - Calle: Nombre de la calle si es visible
        - Coordenadas: Latitud y longitud aproximadas (con la mayor precisión posible)
        - Nivel de confianza: Porcentaje estimado de certeza (0-100%)
        - Evidencia de apoyo: Lista de elementos visuales que respaldan tu conclusión
        - Alternativas posibles: Otras ubicaciones que podrían coincidir
        
        Proporciona únicamente la información que puedas determinar con razonable certeza.
        Si no puedes identificar algún nivel, indica "No determinado".
        
        Responde ÚNICAMENTE en formato JSON para facilitar el procesamiento automático.
        """
    
    def _build_user_prompt(self, metadata: Dict[str, Any]) -> str:
        """Construye el prompt del usuario para la API."""
        image_info = self._extract_image_metadata(metadata)
        yolo_context = self._format_yolo_context(metadata.get('yolo_context', {}))
        json_format = self._get_response_format_template()
        
        return f"""
        Analiza esta imagen y determina su ubicación geográfica (país, ciudad, distrito, barrio, calle) 
        basándote en las características visibles como arquitectura, carteles, vegetación, personas, 
        vehículos y estructura urbana.
        
        {image_info}
        
        INFORMACIÓN ADICIONAL DE OBJETOS DETECTADOS:
        {yolo_context}
        
        INSTRUCCIONES:
        - Utiliza TANTO la imagen visual COMO la información de objetos detectados para tu análisis
        - Los objetos detectados pueden darte pistas importantes sobre el tipo de ubicación
        - Considera la combinación de objetos para inferir contexto geográfico
        - Si detectas vehículos específicos, consideralos para determinar la región/país
        - La presencia de ciertos elementos urbanos puede indicar nivel de desarrollo
        
        Por favor, presenta tus hallazgos en formato JSON con los siguientes campos:
        {json_format}
        """
    
    def _extract_image_metadata(self, metadata: Dict[str, Any]) -> str:
        """Extrae metadatos relevantes de la imagen."""
        return f"""Formato de la imagen: {metadata.get('format', 'desconocido')}
        Dimensiones: {metadata.get('dimensions', (0, 0))}"""
    
    def _get_response_format_template(self) -> str:
        """Obtiene la plantilla del formato de respuesta JSON."""
        return """{
            "country": "nombre del país",
            "city": "nombre de la ciudad",
            "district": "nombre del distrito",
            "neighborhood": "nombre del barrio",
            "street": "nombre de la calle",
            "coordinates": {
                "latitude": valor de latitud (número decimal),
                "longitude": valor de longitud (número decimal)
            },
            "confidence": porcentaje de confianza (0-100),
            "supporting_evidence": ["elemento 1", "elemento 2", ...],
            "possible_alternatives": [
                {
                    "country": "país alternativo",
                    "city": "ciudad alternativa",
                    "confidence": porcentaje de confianza (0-100)
                }
            ]
        }"""
        
    def _process_response(self, response: ChatCompletion) -> Dict[str, Any]:
        """Procesa la respuesta de la API."""
        try:
            content = self._extract_response_content(response)
            parsed_json = self._parse_json_response(content)
            return parsed_json
            
        except Exception as e:
            logger.error(f"Error al procesar respuesta: {str(e)}")
            return self._create_parsing_error_response(str(e), content if 'content' in locals() else "No disponible")
    
    def _extract_response_content(self, response: ChatCompletion) -> str:
        """Extrae el contenido de la respuesta de la API."""
        content = response.choices[0].message.content
        return content.strip() if content else ""
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parsea el contenido JSON de la respuesta."""
        # Extraer JSON de marcadores de código
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
        else:
            # Intentar extraer JSON sin formato
            json_match = re.search(r'({[\s\S]*})', content)
            if json_match:
                content = json_match.group(1)
        
        return json.loads(content)
            
    def _create_parsing_error_response(self, error_message: str, raw_content: str) -> Dict[str, Any]:
        """Crea una respuesta de error de parsing."""
        return {
            "error": f"Error al procesar la respuesta: {error_message}",
            "country": "Error de formato",
            "city": "Error de formato",
            "district": "Error de formato",
            "neighborhood": "Error de formato",
            "street": "Error de formato",
            "confidence": 0,
            "supporting_evidence": [],
            "raw_response": raw_content
        }
    
    def _format_yolo_context(self, yolo_context: Dict[str, Any]) -> str:
        """
        Formatea el contexto de YOLO para el prompt de GPT-4 Vision.
        
        Args:
            yolo_context: Contexto de objetos detectados por YOLO
            
        Returns:
            Texto formateado con información de objetos
        """
        if not yolo_context or "error" in yolo_context:
            return "No hay información adicional de objetos detectados disponible."
        
        context_text = f"""
🔍 ANÁLISIS DE OBJETOS DETECTADOS (YOLO 11):

📊 RESUMEN GENERAL:
- Total de objetos detectados: {yolo_context.get('total_objects', 0)}

📋 OBJETOS POR CATEGORÍA:
{self._format_object_summary(yolo_context.get('object_summary', {}))}

⭐ OBJETOS PROMINENTES (alta confianza y área significativa):
{self._format_prominent_objects(yolo_context.get('prominent_objects', []))}

🗺️ INDICADORES GEOGRÁFICOS:
{self._format_geographic_indicators(yolo_context.get('geographic_indicators', {}))}

💡 CONTEXTO PARA ANÁLISIS GEOGRÁFICO:
- Usa esta información para complementar tu análisis visual
- Los vehículos pueden indicar región (tipos comunes en diferentes países)
- Elementos urbanos sugieren nivel de desarrollo e infraestructura
- Densidad de personas puede indicar tipo de área (comercial, residencial, turística)
- Medios de transporte específicos pueden ser característicos de ciertas regiones
        """
        
        return context_text.strip()
    
    def _format_object_summary(self, object_summary: Dict[str, int]) -> str:
        """Formatea el resumen de objetos."""
        if not object_summary:
            return "- No hay objetos categorizados detectados"
        
        summary_lines = []
        for obj_type, count in sorted(object_summary.items(), key=lambda x: x[1], reverse=True):
            summary_lines.append(f"- {obj_type}: {count} detectado(s)")
        
        return "\n".join(summary_lines[:10])  # Top 10 categorías
    
    def _format_prominent_objects(self, prominent_objects: List[Dict[str, Any]]) -> str:
        """Formatea los objetos prominentes."""
        if not prominent_objects:
            return "- No hay objetos prominentes detectados"
        
        prominent_lines = []
        for obj in prominent_objects[:5]:  # Top 5
            class_name = obj.get('class_name', 'unknown')
            confidence = obj.get('confidence', 0)
            area_percentage = obj.get('area_percentage', 0)
            prominent_lines.append(
                f"- {class_name}: {confidence:.1%} confianza, {area_percentage:.1f}% del área de la imagen"
            )
        
        return "\n".join(prominent_lines)
    
    def _format_geographic_indicators(self, geographic_indicators: Dict[str, Any]) -> str:
        """Formatea los indicadores geográficos."""
        if not geographic_indicators:
            return "- No hay indicadores geográficos específicos detectados"
        
        indicator_lines = []
        
        # Vehículos
        vehicles = geographic_indicators.get('vehicles', [])
        if vehicles:
            vehicle_types = [v['type'] for v in vehicles]
            indicator_lines.append(f"🚗 Vehículos: {', '.join(set(vehicle_types))}")
        
        # Elementos urbanos
        urban_elements = geographic_indicators.get('urban_elements', [])
        if urban_elements:
            urban_types = [u['type'] for u in urban_elements]
            indicator_lines.append(f"🏙️ Elementos urbanos: {', '.join(set(urban_types))}")
        
        # Personas
        people_indicators = geographic_indicators.get('people_indicators', [])
        if people_indicators:
            people_count = len(people_indicators)
            avg_confidence = sum(p['confidence'] for p in people_indicators) / len(people_indicators)
            indicator_lines.append(f"👥 Personas: {people_count} detectadas (confianza promedio: {avg_confidence:.1%})")
        
        # Transporte
        transportation = geographic_indicators.get('transportation', [])
        if transportation:
            transport_types = [t['type'] for t in transportation]
            indicator_lines.append(f"🚲 Transporte: {', '.join(set(transport_types))}")
        
        # Elementos naturales
        natural_elements = geographic_indicators.get('natural_elements', [])
        if natural_elements:
            natural_types = [n['type'] for n in natural_elements]
            indicator_lines.append(f"🌿 Elementos naturales: {', '.join(set(natural_types))}")
        
        return "\n".join(indicator_lines) if indicator_lines else "- No hay indicadores geográficos específicos detectados" 