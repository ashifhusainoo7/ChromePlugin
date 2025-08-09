"""
Enterprise Sentiment Analysis Service
Multi-model sentiment analysis with real-time processing and enterprise features
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Sentiment analysis libraries
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# Audio transcription
import whisper
import torch
import librosa
import soundfile as sf

from app.core.config import get_settings, get_sentiment_config, get_audio_config
from app.core.logging import setup_logging


class SentimentModel(Enum):
    """Available sentiment analysis models"""
    VADER = "vader"
    TEXTBLOB = "textblob"
    TRANSFORMERS = "transformers"


class SentimentLabel(Enum):
    """Sentiment classification labels"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    text: str
    label: SentimentLabel
    confidence: float
    scores: Dict[str, float]
    model_used: str
    timestamp: float
    processing_time: float


@dataclass
class AudioTranscription:
    """Audio transcription result"""
    text: str
    confidence: float
    language: str
    segments: List[Dict]
    processing_time: float


class SentimentAnalyzer:
    """
    Enterprise sentiment analysis service with multiple models and real-time processing
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.sentiment_config = get_sentiment_config()
        self.audio_config = get_audio_config()
        self.logger = setup_logging()
        
        # Initialize models
        self.vader_analyzer = None
        self.transformer_model = None
        self.transformer_tokenizer = None
        self.whisper_model = None
        
        # Performance tracking
        self.analysis_count = 0
        self.total_processing_time = 0.0
        self.model_stats = {model.value: {"count": 0, "avg_time": 0.0} for model in SentimentModel}
        
        # Initialize models asynchronously
        asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize all sentiment analysis models"""
        try:
            self.logger.info("Initializing sentiment analysis models...")
            
            # Initialize VADER
            self.vader_analyzer = SentimentIntensityAnalyzer()
            self.logger.info("VADER sentiment analyzer initialized")
            
            # Initialize Transformer model (if configured)
            if self.sentiment_config["model"] == "transformers":
                model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
                self.transformer_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.transformer_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.transformer_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.transformer_model,
                    tokenizer=self.transformer_tokenizer,
                    return_all_scores=True
                )
                self.logger.info("Transformer sentiment model initialized")
            
            # Initialize Whisper for audio transcription
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.whisper_model = whisper.load_model(
                self.audio_config["whisper_model"],
                device=device
            )
            self.logger.info(f"Whisper model '{self.audio_config['whisper_model']}' initialized on {device}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize models: {str(e)}", exc_info=True)
    
    async def analyze_text(
        self, 
        text: str, 
        model: Optional[SentimentModel] = None
    ) -> SentimentResult:
        """
        Analyze sentiment of text using specified model
        """
        start_time = time.time()
        
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            # Use configured model if not specified
            if model is None:
                model = SentimentModel(self.sentiment_config["model"])
            
            # Perform sentiment analysis
            if model == SentimentModel.VADER:
                result = await self._analyze_with_vader(text)
            elif model == SentimentModel.TEXTBLOB:
                result = await self._analyze_with_textblob(text)
            elif model == SentimentModel.TRANSFORMERS:
                result = await self._analyze_with_transformers(text)
            else:
                raise ValueError(f"Unsupported model: {model}")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            result.timestamp = time.time()
            
            # Update statistics
            self._update_stats(model.value, processing_time)
            
            self.logger.debug(
                f"Sentiment analysis completed",
                text_length=len(text),
                model=model.value,
                label=result.label.value,
                confidence=result.confidence,
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {str(e)}", exc_info=True)
            raise
    
    async def _analyze_with_vader(self, text: str) -> SentimentResult:
        """Analyze sentiment using VADER"""
        if not self.vader_analyzer:
            raise RuntimeError("VADER analyzer not initialized")
        
        scores = self.vader_analyzer.polarity_scores(text)
        compound = scores['compound']
        
        # Determine label based on compound score
        if compound >= self.sentiment_config["threshold_positive"]:
            label = SentimentLabel.POSITIVE
        elif compound <= self.sentiment_config["threshold_negative"]:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL
        
        # Use absolute compound score as confidence
        confidence = abs(compound)
        
        return SentimentResult(
            text=text,
            label=label,
            confidence=confidence,
            scores=scores,
            model_used="vader",
            timestamp=0,  # Will be set by caller
            processing_time=0  # Will be set by caller
        )
    
    async def _analyze_with_textblob(self, text: str) -> SentimentResult:
        """Analyze sentiment using TextBlob"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Determine label based on polarity
        if polarity >= self.sentiment_config["threshold_positive"]:
            label = SentimentLabel.POSITIVE
        elif polarity <= self.sentiment_config["threshold_negative"]:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL
        
        # Use absolute polarity as confidence
        confidence = abs(polarity)
        
        scores = {
            "polarity": polarity,
            "subjectivity": subjectivity
        }
        
        return SentimentResult(
            text=text,
            label=label,
            confidence=confidence,
            scores=scores,
            model_used="textblob",
            timestamp=0,
            processing_time=0
        )
    
    async def _analyze_with_transformers(self, text: str) -> SentimentResult:
        """Analyze sentiment using Transformer model"""
        if not self.transformer_pipeline:
            raise RuntimeError("Transformer model not initialized")
        
        # Run inference
        results = self.transformer_pipeline(text)
        
        # Process results
        scores_dict = {result['label'].lower(): result['score'] for result in results}
        
        # Find the label with highest confidence
        best_result = max(results, key=lambda x: x['score'])
        label_mapping = {
            'positive': SentimentLabel.POSITIVE,
            'negative': SentimentLabel.NEGATIVE,
            'neutral': SentimentLabel.NEUTRAL
        }
        
        label = label_mapping.get(best_result['label'].lower(), SentimentLabel.NEUTRAL)
        confidence = best_result['score']
        
        return SentimentResult(
            text=text,
            label=label,
            confidence=confidence,
            scores=scores_dict,
            model_used="transformers",
            timestamp=0,
            processing_time=0
        )
    
    async def transcribe_audio(self, audio_data: Union[bytes, np.ndarray, str]) -> AudioTranscription:
        """
        Transcribe audio to text using Whisper
        """
        start_time = time.time()
        
        try:
            if not self.whisper_model:
                raise RuntimeError("Whisper model not initialized")
            
            # Handle different input types
            if isinstance(audio_data, bytes):
                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            elif isinstance(audio_data, str):
                # Load from file path
                audio_array, sr = librosa.load(audio_data, sr=self.audio_config["sample_rate"])
            elif isinstance(audio_data, np.ndarray):
                audio_array = audio_data
            else:
                raise ValueError("Unsupported audio data type")
            
            # Ensure correct sample rate
            if hasattr(audio_array, 'shape') and len(audio_array.shape) > 1:
                # Convert stereo to mono if needed
                audio_array = librosa.to_mono(audio_array.T)
            
            # Transcribe using Whisper
            result = self.whisper_model.transcribe(
                audio_array,
                language="en",  # Can be made configurable
                task="transcribe"
            )
            
            processing_time = time.time() - start_time
            
            transcription = AudioTranscription(
                text=result["text"],
                confidence=self._calculate_whisper_confidence(result),
                language=result.get("language", "en"),
                segments=result.get("segments", []),
                processing_time=processing_time
            )
            
            self.logger.info(
                "Audio transcription completed",
                text_length=len(transcription.text),
                processing_time=processing_time,
                language=transcription.language
            )
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"Audio transcription failed: {str(e)}", exc_info=True)
            raise
    
    def _calculate_whisper_confidence(self, whisper_result: Dict) -> float:
        """Calculate confidence score from Whisper result"""
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.5  # Default confidence
        
        # Average the confidence scores from all segments
        confidences = []
        for segment in segments:
            if "avg_logprob" in segment:
                # Convert log probability to confidence (0-1)
                confidence = np.exp(segment["avg_logprob"])
                confidences.append(confidence)
        
        return np.mean(confidences) if confidences else 0.5
    
    async def analyze_audio_sentiment(
        self, 
        audio_data: Union[bytes, np.ndarray, str],
        model: Optional[SentimentModel] = None
    ) -> Tuple[AudioTranscription, SentimentResult]:
        """
        Transcribe audio and analyze sentiment in one operation
        """
        try:
            # Transcribe audio
            transcription = await self.transcribe_audio(audio_data)
            
            # Analyze sentiment of transcribed text
            if transcription.text.strip():
                sentiment = await self.analyze_text(transcription.text, model)
            else:
                # No text to analyze
                sentiment = SentimentResult(
                    text="",
                    label=SentimentLabel.NEUTRAL,
                    confidence=0.0,
                    scores={},
                    model_used=model.value if model else self.sentiment_config["model"],
                    timestamp=time.time(),
                    processing_time=0.0
                )
            
            return transcription, sentiment
            
        except Exception as e:
            self.logger.error(f"Audio sentiment analysis failed: {str(e)}", exc_info=True)
            raise
    
    async def batch_analyze(
        self, 
        texts: List[str], 
        model: Optional[SentimentModel] = None
    ) -> List[SentimentResult]:
        """
        Analyze sentiment for multiple texts in batch
        """
        try:
            tasks = [self.analyze_text(text, model) for text in texts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Batch analysis failed for text {i}: {str(result)}")
                else:
                    valid_results.append(result)
            
            return valid_results
            
        except Exception as e:
            self.logger.error(f"Batch sentiment analysis failed: {str(e)}", exc_info=True)
            raise
    
    def _update_stats(self, model: str, processing_time: float):
        """Update performance statistics"""
        self.analysis_count += 1
        self.total_processing_time += processing_time
        
        # Update model-specific stats
        if model in self.model_stats:
            stats = self.model_stats[model]
            stats["count"] += 1
            stats["avg_time"] = (stats["avg_time"] * (stats["count"] - 1) + processing_time) / stats["count"]
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        avg_processing_time = (
            self.total_processing_time / self.analysis_count 
            if self.analysis_count > 0 else 0.0
        )
        
        return {
            "total_analyses": self.analysis_count,
            "average_processing_time": avg_processing_time,
            "total_processing_time": self.total_processing_time,
            "models": self.model_stats,
            "whisper_model": self.audio_config["whisper_model"],
            "default_sentiment_model": self.sentiment_config["model"]
        }
    
    async def is_negative_sentiment(
        self, 
        text: str, 
        threshold: Optional[float] = None
    ) -> bool:
        """
        Quick check if text has negative sentiment above threshold
        """
        try:
            result = await self.analyze_text(text)
            threshold = threshold or abs(self.sentiment_config["threshold_negative"])
            
            return (
                result.label == SentimentLabel.NEGATIVE and 
                result.confidence >= threshold
            )
            
        except Exception as e:
            self.logger.error(f"Negative sentiment check failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Clear GPU memory if using CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Sentiment analyzer cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}", exc_info=True)