#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente LLM para comunicación con modelos de lenguaje.
Responsabilidad única: Manejar la comunicación con LLM providers.
"""

import logging
from typing import List, Optional
import openai
from openai.types.chat import ChatCompletionMessageParam

from src.utils.config import get_llm_config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Cliente para comunicación con modelos de lenguaje.
    Soporta múltiples providers (Docker, OpenAI).
    """
    
    def __init__(self):
        """Inicializa el cliente LLM."""
        self.llm_config = get_llm_config()
        self.provider = self.llm_config["provider"]
        self.config = self.llm_config["config"]
        self._setup_client()
        
        logger.info(f"LLMClient inicializado: {self.provider}")
    
    def _setup_client(self) -> None:
        """Configura el cliente según el proveedor."""
        if self.provider == "docker":
            logger.info(f"Docker Model: {self.config['model']}")
            self.client = openai.OpenAI(
                base_url=self.config["base_url"],
                api_key=self.config["api_key"]
            )
        elif self.provider == "openai":
            logger.info("OpenAI API configurada")
            self.client = openai.OpenAI(api_key=self.config["api_key"])
    
    def create_chat_completion(self, 
                             messages: List[ChatCompletionMessageParam],
                             temperature: Optional[float] = None) -> str:
        """
        Crea completion de chat usando el proveedor configurado.
        
        Args:
            messages: Lista de mensajes para el chat
            temperature: Temperatura para la generación (opcional)
            
        Returns:
            str: Respuesta del modelo
        """
        temp = (temperature if temperature is not None 
                else self.config["temperature"])
        
        try:
            if self.provider == "docker":
                response = self._create_docker_completion(messages, temp)
            elif self.provider == "openai":
                response = self._create_openai_completion(messages, temp)
            
            content = response.choices[0].message.content
            return content if content else ""
            
        except Exception as e:
            logger.error(f"Error en {self.provider} completion: {e}")
            raise
    
    def _create_docker_completion(self, 
                                messages: List[ChatCompletionMessageParam],
                                temperature: float):
        """Crea completion usando Docker Models."""
        return self.client.chat.completions.create(
            model=self.config["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=self.config["max_tokens"],
            timeout=self.config.get("timeout", 60)
        )
    
    def _create_openai_completion(self, 
                                messages: List[ChatCompletionMessageParam],
                                temperature: float):
        """Crea completion usando OpenAI API."""
        return self.client.chat.completions.create(
            model=self.config["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=self.config["max_tokens"]
        )
    
    def get_provider_info(self) -> dict:
        """Retorna información del proveedor configurado."""
        return {
            "provider": self.provider,
            "model": self.config["model"]
        } 