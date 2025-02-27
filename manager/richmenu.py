"""
Rich Menu Framework using the Python Line SDK.

This module provides composable and reusable objects to build, link, trigger,
and manage rich menus using the Line Messaging API.

Classes:
  - RichMenuBuilder: A builder for creating RichMenu objects.
  - RichMenuManager: A facade to manage rich menus via the LineBotApi.
"""

from linebot.v3.messaging import AsyncMessagingApi, AsyncMessagingApiBlob
from linebot.v3.messaging.models import CreateRichMenuAliasRequest
from linebot.models import (
    RichMenu,
    RichMenuSize,
    RichMenuArea,
    RichMenuBounds,
    URIAction,
    MessageAction,
    RichMenuSwitchAction,
    PostbackAction  # New import for postback actions
)
import json
import os
from PIL import Image

class RichMenuBuilder:
    """
    Builder class for constructing RichMenu objects in a composable way.
    
    Example:
        builder = RichMenuBuilder("My Rich Menu") \\
            .set_size(2500, 1686) \\
            .set_selected(False) \\
            .set_chat_bar_text("Tap here") \\
            .add_area(0, 0, 1250, 843, MessageAction(label="Say Hi", text="Hi"))
        
        rich_menu = builder.build()
    """

    def __init__(self, name):
        self.size = None
        self.selected = False
        self.name = name
        self.chat_bar_text = ""
        self.areas = []
    
    def set_size(self, width: int, height: int):
        """
        Set the size of the rich menu.
        """
        self.size = RichMenuSize(width=width, height=height)
        return self

    def set_selected(self, selected: bool):
        """
        Set whether this rich menu is selected by default.
        """
        self.selected = selected
        return self

    def set_chat_bar_text(self, text: str):
        """
        Set the chat bar text of the rich menu.
        """
        self.chat_bar_text = text
        return self

    def add_area(self, x: int, y: int, width: int, height: int, action):
        """
        Add an interactive area with given bounds and action.
        
        Args:
            x (int): The x-coordinate of the area's top-left corner.
            y (int): The y-coordinate of the area's top-left corner.
            width (int): The width of the area.
            height (int): The height of the area.
            action: An action object (e.g., MessageAction, URIAction, etc.).
        """
        bounds = RichMenuBounds(x=x, y=y, width=width, height=height)
        area = RichMenuArea(bounds=bounds, action=action)
        self.areas.append(area)
        return self

    def build(self) -> RichMenu:
        """
        Build and return a RichMenu object.
        """
        return RichMenu(
            size=self.size,
            selected=self.selected,
            name=self.name,
            chat_bar_text=self.chat_bar_text,
            areas=self.areas
        )

class RichMenuManager:
    """
    Manager class for handling rich menu operations.
    
    This class provides a facade to create, upload, link, and delete rich menus
    using the LineBotApi.
    """
    def __init__(self, api: AsyncMessagingApi, api_blob: AsyncMessagingApiBlob):
        """
        Initialize the RichMenuManager with the given channel access token.
        """
        self.line_bot_api = api
        self.line_bot_api_blob = api_blob
        self.rich_menus = {}
        
    def create_rich_menu(self, builder: RichMenuBuilder) -> str:
        """
        Create a rich menu from a RichMenuBuilder instance.
        
        Returns:
            str: The ID of the created rich menu.
        """
        rich_menu_object = builder.build()
        rich_menu_id = self.line_bot_api.create_rich_menu_alias(create_rich_menu_alias_request=rich_menu_object)
        self.rich_menus[rich_menu_id] = rich_menu_object
        return rich_menu_id

    def upload_rich_menu_image(self, rich_menu_id: str, image_path: str):
        """
        Upload an image file to be associated with the rich menu.
        It automatically fetches the image's width and height before uploading.
        
        Args:
            rich_menu_id (str): The ID of the rich menu.
            image_path (str): The file path to the image.
        """
        with open(image_path, 'rb') as f:
            self.line_bot_api_blob.set_rich_menu_image(rich_menu_id, body=f, _headers={"Content-Type": "image/png"})

    def create_alias_rich_menu(self, rich_menu_id: str, alias: str):
        """
        Create a rich menu alias.
        """
        self.line_bot_api.create_rich_menu_alias(create_rich_menu_alias_request=CreateRichMenuAliasRequest(
            rich_menu_alias_id=alias,
            rich_menu_id=rich_menu_id
        ))
    
    def delete_rich_menu(self, rich_menu_id: str):
        """
        Delete a rich menu by its ID.
        """
        self.line_bot_api.delete_rich_menu(rich_menu_id)

    def link_rich_menu_to_user(self, user_id: str, rich_menu_id: str):
        """
        Link a rich menu to a specific user.
        
        Args:
            user_id (str): The user's ID.
            rich_menu_id (str): The rich menu's ID.
        """
        result = self.line_bot_api.link_rich_menu_id_to_user(user_id, rich_menu_id, async_req=True)
        return result.get()

    def unlink_rich_menu_from_user(self, user_id: str):
        """
        Unlink the rich menu from a specific user.
        
        Args:
            user_id (str): The user's ID.
        """
        result = self.line_bot_api.unlink_rich_menu_id_from_user(user_id, async_req=True)
        return result.get()

def load_rich_menu_configs():
    """
    Loads rich menu configurations from the JSON file.
    """
    config_path = os.path.join("./category", "rich_menu.json")
    with open(config_path, 'r', encoding='utf8') as f:
        return json.load(f)

def build_rich_menu_from_config(name, rich_menu_config) -> RichMenuBuilder:
    """
    Builds a RichMenuBuilder instance from a grid-based configuration.
    
    The configuration must include:
      - file: image file name to auto-fetch dimensions
      - selected: bool
      - name: str
      - chat_bar_text: str
      - grid: { rows, columns }
      - actions: list of action objects
    """
    image_file = rich_menu_config.get("file")
    if image_file:
        image_path = os.path.join("./templates", image_file)
        with Image.open(image_path) as img:
            width, height = img.size

    rows = rich_menu_config["grid"]["rows"]
    cols = rich_menu_config["grid"]["columns"]
    cell_width = width // cols
    cell_height = height // rows

    builder = RichMenuBuilder(name)\
        .set_size(width, height)\
        .set_selected(rich_menu_config["selected"])\
        .set_chat_bar_text(rich_menu_config["chat_bar_text"])

    for index, action_cfg in enumerate(rich_menu_config["actions"]):
        if 'type' not in action_cfg:
            continue
        col = index % cols
        row = index // cols
        x = col * cell_width
        y = row * cell_height
        if action_cfg["type"] == "message":
            act = MessageAction(action_cfg["label"], action_cfg["text"])
        elif action_cfg["type"] == "uri":
            act = URIAction(action_cfg["label"], action_cfg["uri"])
        elif action_cfg["type"] == "switch":
            act = RichMenuSwitchAction(
                action_cfg["label"],
                action_cfg["rich_menu_alias_id"],
                action_cfg["data"])
        elif action_cfg["type"] == "postback":
            act = PostbackAction(
                action_cfg["label"],
                action_cfg["data"])
        else:
            raise ValueError(f"Unknown action type: {action_cfg['type']} at index {index} in menu {name}")
        builder.add_area(x, y, cell_width, cell_height, act)
    return builder
