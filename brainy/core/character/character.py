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
        
        # Initialize conversation preferences
        self._conversation_preferences: Dict[str, str] = {}
        self._preferences_file = self._characters_dir.parent / "preferences" / "character_preferences.json"
        
        # Load characters from files
        self._load_characters()
        
        # Load conversation preferences
        self._load_conversation_preferences()
        
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
            The character if found, None otherwise
        """
        # Make lookup case-insensitive by comparing lowercase versions
        character_id_lower = character_id.lower()
        for id, character in self._characters.items():
            if id.lower() == character_id_lower:
                return character
        
        return None
    
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
    
    def get_character_for_conversation(self, conversation_id: str) -> Character:
        """
        Get the character for a conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            The character associated with the conversation,
            or the default character if none is set
        """
        # Try to get the character_id for this conversation from preferences
        character_id = self._conversation_preferences.get(conversation_id)
        
        # If no preference or character doesn't exist, return default
        if not character_id:
            return self.get_default_character()
            
        # Make lookup case-insensitive
        character = self.get_character(character_id)
        if not character:
            # Character not found, return default
            return self.get_default_character()
            
        return character
    
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
    
    def create_character(
        self,
        character_id: str,
        name: str,
        system_prompt: str,
        description: str = "",
        greeting: Optional[str] = None,
        farewell: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Character]:
        """
        Create a new character.
        
        Args:
            character_id: Unique identifier for the character
            name: Display name of the character
            system_prompt: System prompt that defines the character's personality
            description: Description of the character
            greeting: Optional custom greeting message
            farewell: Optional custom farewell message
            avatar_url: Optional URL to the character's avatar image
            metadata: Optional additional metadata for the character
            
        Returns:
            The created character, or None if creation failed
        """
        # Check if character ID already exists
        if character_id in self._characters:
            logger.warning(f"Character with ID '{character_id}' already exists")
            return None
        
        # Create the character
        character = Character(
            character_id=character_id,
            name=name,
            system_prompt=system_prompt,
            description=description,
            greeting=greeting,
            farewell=farewell,
            avatar_url=avatar_url,
            metadata=metadata or {}
        )
        
        # Add the character to the manager
        self.add_character(character)
        
        logger.info(f"Created character '{character.name}' with ID '{character_id}'")
        
        return character
        
    def edit_character(
        self,
        character_id: str,
        **updates
    ) -> Optional[Character]:
        """
        Edit an existing character.
        
        Args:
            character_id: ID of the character to edit
            **updates: Field updates for the character
            
        Returns:
            The updated character, or None if the character wasn't found
        """
        # Check if character exists
        if character_id not in self._characters:
            logger.warning(f"Character with ID '{character_id}' does not exist")
            return None
        
        # Get the current character data
        character = self._characters[character_id]
        character_data = character.to_dict()
        
        # Update the character data
        for field, value in updates.items():
            if field in character_data and value is not None:
                character_data[field] = value
        
        # Create a new character with the updated data
        updated_character = Character.from_dict(character_data)
        
        # Add the updated character to the manager
        self.add_character(updated_character)
        
        logger.info(f"Updated character '{updated_character.name}' with ID '{character_id}'")
        
        return updated_character
        
    def delete_character(self, character_id: str) -> bool:
        """
        Delete a character.
        
        Args:
            character_id: ID of the character to delete
            
        Returns:
            True if the character was deleted, False otherwise
            
        Raises:
            ValueError: If the character is the default character or doesn't exist
        """
        # Make lookup case-insensitive
        character_to_delete = self.get_character(character_id)
        
        # Check if the character exists
        if not character_to_delete:
            logger.warning(f"Cannot delete character '{character_id}': character not found")
            raise ValueError(f"Character '{character_id}' not found")
        
        # Get the actual character ID with correct case
        actual_character_id = character_to_delete.character_id
        
        # Check if it's the default character
        if actual_character_id == self._default_character_id:
            logger.warning(f"Cannot delete default character '{actual_character_id}'")
            raise ValueError("Cannot delete the default character")
        
        # Delete the character from memory
        logger.info(f"Deleting character: {actual_character_id}")
        if actual_character_id in self._characters:
            del self._characters[actual_character_id]
        
        # Delete the character file if it exists
        character_file = self._get_character_file_path(actual_character_id)
        if character_file.exists():
            try:
                character_file.unlink()  # Delete the file
                logger.info(f"Deleted character file: {character_file}")
            except Exception as e:
                logger.error(f"Error deleting character file {character_file}: {e}")
                # Continue anyway - we've already removed it from memory
        
        # Remove from conversation preferences if present
        for conv_id, char_id in list(self._conversation_preferences.items()):
            if char_id.lower() == actual_character_id.lower():
                # Reset this conversation to use the default character
                self._conversation_preferences[conv_id] = self._default_character_id
        
        # Save updated preferences
        self._save_conversation_preferences()
        
        return True

    def _load_conversation_preferences(self) -> None:
        """Load conversation character preferences from file."""
        try:
            if self._preferences_file.exists():
                with open(self._preferences_file, "r", encoding="utf-8") as f:
                    self._conversation_preferences = json.load(f)
                logger.debug(f"Loaded character preferences for {len(self._conversation_preferences)} conversations")
            else:
                logger.debug("No character preferences file found, using defaults")
        except Exception as e:
            logger.error(f"Error loading character preferences: {e}")
            self._conversation_preferences = {}
            
    def _save_conversation_preferences(self) -> None:
        """Save conversation character preferences to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self._preferences_file.parent, exist_ok=True)
            
            with open(self._preferences_file, "w", encoding="utf-8") as f:
                json.dump(self._conversation_preferences, f, indent=2)
            logger.debug(f"Saved character preferences for {len(self._conversation_preferences)} conversations")
        except Exception as e:
            logger.error(f"Error saving character preferences: {e}")
            
    def _get_character_file_path(self, character_id: str) -> Path:
        """Get the path to a character file."""
        return self._characters_dir / f"{character_id}.json"


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