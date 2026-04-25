#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de chat contextual para análisis de imágenes.

Permite hacer preguntas sobre imágenes ya analizadas usando YOLO + GPT-4 Vision.

Persistencia
------------
Las sesiones se almacenan en SQLite vía :class:`ChatSessionStore`, de forma
que el contexto sobrevive a reinicios del contenedor. La ruta de la base
de datos se controla con la variable de entorno ``CHAT_DB_PATH`` (por
defecto ``./data/chat_sessions.db`` relativo al CWD).
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

from openai import OpenAI

from src.services.chat_session_store import ChatSessionStore
from src.utils.config import get_llm_config

logger = logging.getLogger(__name__)


def _default_db_path() -> str:
    """Resolve the SQLite path used when ``CHAT_DB_PATH`` is unset.

    The path is anchored to the project root rather than the current
    working directory so the same file is used whether the app is
    started from ``src/`` or from the repo root.
    """
    env_value = os.environ.get("CHAT_DB_PATH")
    if env_value:
        return env_value
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    return os.path.join(project_root, "data", "chat_sessions.db")


class ChatService:
    """
    Servicio que maneja conversaciones contextuales sobre imágenes analizadas.
    Combina información de YOLO y GPT-4 Vision para responder preguntas específicas.
    """

    MAX_SESSIONS = 50
    SESSION_TTL_HOURS = 2

    def __init__(self, db_path: str | None = None) -> None:
        """Initialise the service with a persistent session store.

        Parameters
        ----------
        db_path:
            Optional override for the SQLite path. When ``None``, the
            value of ``CHAT_DB_PATH`` (or the project-root default) is
            used. Tests typically inject a tmp path here.
        """
        llm_config = get_llm_config()
        self.provider = llm_config["provider"]
        self.config = llm_config["config"]
        self.client: OpenAI | None = self._setup_client()
        self.store = ChatSessionStore(db_path or _default_db_path())
        logger.info(
            "Servicio de chat contextual inicializado con provider: %s (db=%s)",
            self.provider,
            self.store.db_path,
        )

    def _setup_client(self) -> OpenAI | None:
        """Configura el cliente segun el proveedor."""
        if self.provider == "groq":
            vision_model = self.config.get(
                "vision_model", "meta-llama/llama-4-scout-17b-16e-instruct"
            )
            self.config["model"] = vision_model
            return OpenAI(base_url=self.config["base_url"], api_key=self.config["api_key"])
        if self.provider == "openai":
            api_key = self.config.get("api_key")
            if api_key:
                return OpenAI(api_key=api_key)
        if self.provider == "docker":
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                from src.utils.config import get_openai_config

                self.config = get_openai_config()
                return OpenAI(api_key=api_key)
        logger.warning("Chat contextual no disponible para provider: %s", self.provider)
        return None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def store_analysis_context(
        self,
        session_id: str,
        analysis_results: dict[str, Any],
        yolo_results: dict[str, Any],
        image_filename: str,
        encoded_image: str | None = None,
        image_format: str = "jpeg",
    ) -> None:
        """
        Almacena el contexto de un análisis para futuras consultas.

        Args:
            session_id: ID único de la sesión.
            analysis_results: Resultados del análisis geográfico.
            yolo_results: Resultados de detección YOLO.
            image_filename: Nombre del archivo de imagen.
            encoded_image: Imagen codificada en base64 (preguntas visuales).
            image_format: Formato de la imagen (jpeg, png, etc.).
        """
        self._cleanup_expired_sessions()
        self.store.store(
            session_id,
            image_filename=image_filename,
            geographic_analysis=analysis_results,
            yolo_detection=yolo_results,
            encoded_image=encoded_image,
            image_format=image_format,
            chat_history=[],
        )
        logger.info("Contexto almacenado para sesion: %s", session_id)

    def _cleanup_expired_sessions(self) -> None:
        """Elimina sesiones expiradas y aplica el límite máximo (LRU)."""
        self.store.cleanup_expired(self.SESSION_TTL_HOURS)
        # ``-1`` because we are about to insert one more row; keeping
        # the cap below MAX_SESSIONS avoids breaching it momentarily.
        self.store.enforce_max_sessions(max(1, self.MAX_SESSIONS - 1))

    def ask_question(self, session_id: str, question: str) -> dict[str, Any]:
        """
        Procesa una pregunta sobre la imagen analizada.

        Args:
            session_id: ID de la sesión.
            question: Pregunta del usuario.

        Returns:
            Respuesta del chat con contexto.
        """
        try:
            self.store.cleanup_expired(self.SESSION_TTL_HOURS)
            context = self.store.get(session_id)
            if context is None:
                return {
                    "error": "No hay contexto de análisis disponible para esta sesión",
                    "response": "Por favor, analiza una imagen primero antes de hacer preguntas.",
                    "status": "error",
                }

            if self._is_visual_question(question) and context.get("encoded_image"):
                logger.info("Pregunta visual detectada para sesion %s", session_id)
                return self._handle_visual_question(session_id, question, context)

            system_prompt = self._build_chat_system_prompt(context)
            user_prompt = self._build_chat_user_prompt(question, context)

            messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
            for chat_entry in context.get("chat_history", []):
                messages.append({"role": "user", "content": chat_entry["question"]})
                messages.append({"role": "assistant", "content": chat_entry["response"]})
            messages.append({"role": "user", "content": user_prompt})

            if self.client is None:
                return {
                    "error": "LLM client not configured",
                    "response": "El servicio de chat no está disponible en esta configuración.",
                    "status": "error",
                }

            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,  # type: ignore[arg-type]
                temperature=0.3,
                max_tokens=1000,
            )

            answer_raw = response.choices[0].message.content
            answer = answer_raw.strip() if answer_raw else ""

            self._append_history(
                session_id,
                context,
                {
                    "question": question,
                    "response": answer,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return {
                "response": answer,
                "question": question,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            }

        except (ValueError, KeyError) as exc:
            logger.error("Error de datos en chat contextual: %s", exc)
            return {
                "error": str(exc),
                "response": "Lo siento, los datos de la sesión no son válidos.",
                "status": "error",
            }
        except OSError as exc:
            logger.error("Error de I/O en chat contextual: %s", exc)
            return {
                "error": str(exc),
                "response": "Lo siento, ocurrió un error de almacenamiento.",
                "status": "error",
            }

    def get_chat_history(self, session_id: str) -> list[dict[str, Any]]:
        """Obtiene el historial de chat para una sesión."""
        context = self.store.get(session_id)
        if context is None:
            return []
        return context.get("chat_history", []) or []

    def clear_chat_history(self, session_id: str) -> bool:
        """Limpia el historial de chat para una sesión."""
        return self.store.update_field(session_id, "chat_history", [])

    def get_context_summary(self, session_id: str) -> dict[str, Any]:
        """Obtiene un resumen del contexto de análisis."""
        context = self.store.get(session_id)
        if context is None:
            return {"error": "No hay contexto disponible"}

        geo_analysis = context.get("geographic_analysis") or {}
        yolo_detection = context.get("yolo_detection") or {}

        return {
            "image_filename": context.get("image_filename"),
            "timestamp": context.get("timestamp"),
            "geographic_results": {
                "country": geo_analysis.get("country", "No determinado"),
                "city": geo_analysis.get("city", "No determinado"),
                "confidence": geo_analysis.get("confidence", 0),
            },
            "yolo_results": {
                "total_objects": yolo_detection.get("total_objects", 0),
                "categories": len(yolo_detection.get("object_summary", {})),
                "top_objects": list(yolo_detection.get("object_summary", {}).keys())[:5],
            },
            "chat_messages": len(context.get("chat_history", []) or []),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _append_history(
        self,
        session_id: str,
        context: dict[str, Any],
        entry: dict[str, Any],
    ) -> None:
        """Append a chat entry and persist the new history list.

        ``context`` is the dict snapshot already loaded by the caller;
        we mutate it in place so any downstream logic in the same call
        sees the appended turn without a second SELECT.
        """
        history = list(context.get("chat_history") or [])
        history.append(entry)
        context["chat_history"] = history
        self.store.update_field(session_id, "chat_history", history)

    def _build_chat_system_prompt(self, context: dict[str, Any]) -> str:
        """Construye el prompt de sistema para el chat."""
        geo_analysis = context.get("geographic_analysis") or {}
        yolo_detection = context.get("yolo_detection") or {}

        return f"""
        Eres un asistente especializado en análisis de imágenes que puede responder preguntas
        sobre una imagen que ya fue analizada usando YOLO 11 para detección de objetos y
        GPT-4 Vision para análisis geográfico.

        CONTEXTO DE LA IMAGEN ANALIZADA:
        - Archivo: {context.get("image_filename")}
        - Fecha de análisis: {context.get("timestamp")}

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

    def _build_chat_user_prompt(self, question: str, context: dict[str, Any]) -> str:
        """Construye el prompt del usuario para el chat."""
        return f"""
        Pregunta sobre la imagen "{context.get("image_filename")}":

        {question}

        Por favor responde usando toda la información disponible del análisis.
        """

    def get_suggested_questions(self, session_id: str) -> list[str]:
        """Genera preguntas sugeridas basadas en el contexto."""
        context = self.store.get(session_id)
        if context is None:
            return []

        yolo_detection = context.get("yolo_detection") or {}
        geo_analysis = context.get("geographic_analysis") or {}
        suggestions: list[str] = []

        if yolo_detection.get("total_objects", 0) > 0:
            suggestions.append("¿Cuántos objetos detectó YOLO exactamente?")
            top_objects = list(yolo_detection.get("object_summary", {}).keys())
            if top_objects:
                suggestions.append(f"¿Puedes describir los {top_objects[0]} que detectaste?")

        if geo_analysis.get("confidence", 0) > 0:
            suggestions.append(
                f"¿Cómo determinaste que era {geo_analysis.get('country', 'este país')}?"
            )
            suggestions.append("¿Qué nivel de confianza tienes en el análisis?")

        if context.get("encoded_image"):
            top_objects = list(yolo_detection.get("object_summary", {}).keys())
            if top_objects:
                suggestions.append(f"¿De qué color son los {top_objects[0]} en la imagen?")
                suggestions.append(f"¿Cómo es el aspecto de los {top_objects[0]}?")
            suggestions.append("¿Qué colores predominan en la imagen?")
            suggestions.append("¿Puedes describir el estado de los objetos visibles?")

        suggestions.append("¿Cómo te ayudó YOLO a mejorar el análisis geográfico?")
        suggestions.append("¿Qué elementos fueron más importantes para la identificación?")

        return suggestions[:6]

    def _is_visual_question(self, question: str) -> bool:
        """Detecta si una pregunta requiere análisis visual específico."""
        visual_keywords = [
            "color", "colores", "qué color", "de qué color", "rojo", "azul", "verde",
            "amarillo", "negro", "blanco", "gris", "naranja", "rosa", "morado", "violeta",
            "forma", "formas", "aspecto", "apariencia", "tamaño", "grande", "pequeño",
            "alto", "bajo", "ancho", "estrecho", "redondo", "cuadrado", "rectangular",
            "detalle", "detalles", "específico", "exacto", "preciso", "describe",
            "cómo se ve", "cómo es", "qué tal", "marca", "modelo", "tipo",
            "brillo", "luminoso", "oscuro", "claro", "opaco", "transparente",
            "textura", "superficie", "material", "acabado", "estado",
            "patrón", "diseño", "estilo", "rayado", "liso", "rugoso",
            "nuevo", "viejo", "antiguo", "moderno", "deteriorado",
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in visual_keywords)

    def _handle_visual_question(
        self,
        session_id: str,
        question: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Maneja preguntas que requieren análisis visual específico."""
        try:
            visual_prompt = self._build_visual_analysis_prompt(question, context)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": visual_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:image/{context['image_format']};base64,"
                                    f"{context['encoded_image']}"
                                )
                            },
                        },
                    ],
                }
            ]

            if self.client is None:
                return {
                    "error": "LLM client not configured",
                    "response": "El análisis visual no está disponible en esta configuración.",
                    "status": "error",
                }

            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,  # type: ignore[arg-type]
                temperature=0.3,
                max_tokens=1000,
            )

            answer_raw = response.choices[0].message.content
            answer = answer_raw.strip() if answer_raw else ""
            enhanced_answer = self._enhance_visual_response(answer, context)

            self._append_history(
                session_id,
                context,
                {
                    "question": question,
                    "response": enhanced_answer,
                    "timestamp": datetime.now().isoformat(),
                    "type": "visual_analysis",
                },
            )

            return {
                "response": enhanced_answer,
                "question": question,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "analysis_type": "visual_specific",
            }

        except (ValueError, KeyError) as exc:
            logger.error("Error de datos en análisis visual específico: %s", exc)
            return {
                "error": str(exc),
                "response": "Lo siento, no pude analizar los detalles visuales específicos de la imagen.",
                "status": "error",
            }

    def _build_visual_analysis_prompt(self, question: str, context: dict[str, Any]) -> str:
        """Construye un prompt específico para análisis visual."""
        geo_analysis = context.get("geographic_analysis") or {}
        yolo_detection = context.get("yolo_detection") or {}

        return f"""
        Eres un especialista en análisis visual de imágenes. Analiza esta imagen con detalle para responder la siguiente pregunta específica sobre características visuales.

        PREGUNTA ESPECÍFICA: {question}

        CONTEXTO DE LA IMAGEN:
        - Archivo: {context.get("image_filename")}
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

    def _enhance_visual_response(self, visual_response: str, context: dict[str, Any]) -> str:
        """Mejora la respuesta visual con información contextual."""
        geo_analysis = context.get("geographic_analysis") or {}
        yolo_detection = context.get("yolo_detection") or {}

        enhanced_response = f"""
        {visual_response}

        🔍 **Análisis Visual Específico Completado**

        Esta información se basa en:
        • **Análisis visual directo** de la imagen usando GPT-4 Vision
        • **Contexto geográfico**: {geo_analysis.get('country', 'No determinado')}, {geo_analysis.get('city', 'No determinado')}
        • **Objetos detectados**: {yolo_detection.get('total_objects', 0)} objetos identificados

        💡 *Tip*: Puedes hacer más preguntas específicas sobre colores, formas o características visuales de cualquier elemento en la imagen.
        """

        return enhanced_response.strip()
