"""
Character system for Brainy.

This module defines the character system that allows creating different bot personalities.
"""
from typing import Dict, List, Optional, Any
import json
import os
from pathlib import Path

from brainy.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class Character:
    """
    Representation of a bot character with personality and behavior settings.
    """
    
    def __init__(
        self,
        character_id: str,
        name: str,
        system_prompt: str,
        description: str = "",
        greeting: Optional[str] = None,
        farewell: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a character.
        
        Args:
            character_id: Unique identifier for the character
            name: Display name of the character
            system_prompt: System prompt that defines the character's personality
            description: Description of the character
            greeting: Optional custom greeting message
            farewell: Optional custom farewell message
            avatar_url: Optional URL to the character's avatar image
            metadata: Optional additional metadata for the character
        """
        self.character_id = character_id
        self.name = name
        self.system_prompt = system_prompt
        self.description = description
        self.greeting = greeting
        self.farewell = farewell
        self.avatar_url = avatar_url
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary representation."""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "description": self.description,
            "greeting": self.greeting,
            "farewell": self.farewell,
            "avatar_url": self.avatar_url,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create a character from dictionary data."""
        return cls(
            character_id=data["character_id"],
            name=data["name"],
            system_prompt=data["system_prompt"],
            description=data.get("description", ""),
            greeting=data.get("greeting"),
            farewell=data.get("farewell"),
            avatar_url=data.get("avatar_url"),
            metadata=data.get("metadata", {})
        )


class CharacterManager:
    """
    Manager for character definitions.
    
    This manager loads character definitions from JSON files and provides
    access to them. For the MVP, characters are loaded from local files,
    but in the future, they could be stored in a database.
    """
    
    def __init__(self, characters_dir: Optional[str] = None):
        """
        Initialize the character manager.
        
        Args:
            characters_dir: Optional directory path to load characters from.
                If not provided, will use the default directory.
        """
        # Dictionary of characters by ID
        self._characters: Dict[str, Character] = {}
        
        # Default character ID
        self._default_character_id: Optional[str] = None
        
        # Directory to load characters from
        if characters_dir is None:
            # Default to characters directory in the package
            package_dir = Path(__file__).parent.parent.parent
            self._characters_dir = package_dir / "data" / "characters"
        else:
            self._characters_dir = Path(characters_dir)
        
        # Ensure characters directory exists
        os.makedirs(self._characters_dir, exist_ok=True)
        
        # Load characters from files
        self._load_characters()
        
        logger.info(f"Initialized character manager with {len(self._characters)} characters")
    
    def _load_characters(self) -> None:
        """Load characters from JSON files in the characters directory."""
        try:
            # Find all JSON files in the characters directory
            json_files = list(self._characters_dir.glob("*.json"))
            
            if not json_files:
                logger.warning(f"No character files found in {self._characters_dir}")
                # Create a default character if none exist
                self._create_default_character()
                return
            
            # Load each character file
            for file_path in json_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    character = Character.from_dict(data)
                    self._characters[character.character_id] = character
                    
                    # Set the first character as default if none is set
                    if self._default_character_id is None:
                        self._default_character_id = character.character_id
                    
                    # If a character is marked as default in metadata, use it
                    if data.get("metadata", {}).get("is_default", False):
                        self._default_character_id = character.character_id
                    
                    logger.debug(f"Loaded character '{character.name}' from {file_path}")
                except Exception as e:
                    logger.error(f"Error loading character from {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading characters: {e}")
            # Create a default character if there was an error
            self._create_default_character()
    
    def _create_default_character(self) -> None:
        """Create a default character if no characters are found."""
        default_character = Character(
            character_id="default",
            name="Brainy",
            system_prompt=(
                "You are Brainy, a helpful and friendly AI assistant. "
                "You are knowledgeable and can help users with a wide range of tasks. "
                "Your tone is friendly, professional, and concise. "
                "You always aim to provide accurate information and help users achieve their goals."
            ),
            description="A helpful and friendly AI assistant.",
            greeting="Hello! I'm Brainy, your friendly AI assistant. How can I help you today?",
            farewell="Goodbye! It was nice chatting with you. Feel free to message me anytime!",
            metadata={"is_default": True}
        )
        
        self._characters[default_character.character_id] = default_character
        self._default_character_id = default_character.character_id
        
        # Save the default character to a file
        self._save_character(default_character)
        
        logger.info("Created default character 'Brainy'")
    
    def _save_character(self, character: Character) -> None:
        """Save a character to a JSON file."""
        try:
            file_path = self._characters_dir / f"{character.character_id}.json"
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(character.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved character '{character.name}' to {file_path}")
        except Exception as e:
            logger.error(f"Error saving character '{character.name}': {e}")
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """
        Get a character by ID.
        
        Args:
            character_id: ID of the character to get
            
        Returns:
            The character, or None if not found
        """
        return self._characters.get(character_id)
    
    def get_default_character(self) -> Character:
        """
        Get the default character.
        
        Returns:
            The default character
        """
        if self._default_character_id is None or self._default_character_id not in self._characters:
            # This should not happen, but just in case
            self._create_default_character()
        
        return self._characters[self._default_character_id]
    
    def get_all_characters(self) -> List[Character]:
        """
        Get all available characters.
        
        Returns:
            List of all characters
        """
        return list(self._characters.values())
    
    def add_character(self, character: Character) -> None:
        """
        Add a new character or update an existing one.
        
        Args:
            character: The character to add or update
        """
        self._characters[character.character_id] = character
        self._save_character(character)
        
        logger.info(f"Added/updated character '{character.name}'")
    
    def set_default_character(self, character_id: str) -> bool:
        """
        Set the default character.
        
        Args:
            character_id: ID of the character to set as default
            
        Returns:
            True if successful, False if the character does not exist
        """
        if character_id not in self._characters:
            logger.warning(f"Cannot set default character: Character '{character_id}' does not exist")
            return False
        
        # Update the old default character's metadata
        if self._default_character_id is not None and self._default_character_id in self._characters:
            old_default = self._characters[self._default_character_id]
            old_default.metadata.pop("is_default", None)
            self._save_character(old_default)
        
        # Set the new default character
        self._default_character_id = character_id
        
        # Update the character's metadata
        character = self._characters[character_id]
        character.metadata["is_default"] = True
        self._save_character(character)
        
        logger.info(f"Set default character to '{character.name}'")
        
        return True


# Singleton instance
_character_manager: Optional[CharacterManager] = None


def get_character_manager() -> CharacterManager:
    """
    Get the character manager instance.
    
    Returns:
        The character manager instance
    """
    global _character_manager
    if _character_manager is None:
        _character_manager = CharacterManager()
    
    return _character_manager 