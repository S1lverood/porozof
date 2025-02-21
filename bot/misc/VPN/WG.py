import json
import logging
import os
import aiofiles
import httpx
from bot.database.methods.update import server_space_update

class WireGuard:
    """
    Класс для управления пользователями на WireGuard VPN серверах.
    """
    NAME_VPN = 'WireGuard'
    servers = json.loads(os.getenv("WG_SERVERS", """{
        "1": {"name": "WireGuard | Амстердам🇳🇱", "url": "http://77.238.241.8:8080"},
        "2": {"name": "WireGuard | Амстердам2🇳🇱", "url": "http://194.246.83.231:8080"},
        "3": {"name": "WireGuard | Амстердам3🇳🇱", "url": "http://89.110.87.122:8080"},
        "4": {"name": "WireGuard | Амстердам4🇳🇱", "url": "http://77.238.234.122:8080"}
    }"""))

    def __init__(self, chat_id, server="all"):
        """
        Инициализация объекта WireGuard.

        :param chat_id: Идентификатор чата пользователя.
        :param server: Идентификатор сервера или "all" для всех.
        """
        self.chat_id = chat_id
        self.s_id = server
        self.server = self.servers.get(server) if server != "all" else "all"

    async def add_user(self) -> str:
        """
        Добавляет пользователя на сервер WireGuard.
        Удаляет пользователя с других серверов перед добавлением.

        :return: Путь к конфигурационному файлу WireGuard.
        """
        try:
            async with httpx.AsyncClient() as client:
                # Удаление пользователя с других серверов
                if self.server != "all":
                    for s_id, server_info in self.servers.items():
                        if s_id != self.s_id:
                            await self._delete_user_from_server(client, server_info['url'],s_id)

                # Добавление пользователя на выбранный сервер
                file_path = await self._create_user_on_server(client)
                return file_path
        except Exception as e:
            logging.error(f"Error in add_user: {e}")
            raise

    async def delete_user(self):
        """
        Удаляет пользователя с сервера или всех серверов.
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.server == "all":
                    for s_id,server_info in self.servers.items():
                        await self._delete_user_from_server(client, server_info['url'],s_id)
                else:
                    await self._delete_user_from_server(client, self.server['url'],int(self.s_id))
        except Exception as e:
            logging.error(f"Error in delete_user: {e}")
            raise

    async def _create_user_on_server(self, client: httpx.AsyncClient) -> str:
        """
        Добавляет пользователя на конкретный сервер.

        :param client: Асинхронный клиент httpx.
        :return: Путь к конфигурационному файлу WireGuard.
        """
        url = self.server['url'] + "/createWG"
        data = {"chat_id": self.chat_id}
        response = await client.post(url, json=data)
        response.raise_for_status()

        response_data = response.json()
        file_path = f'/app/bot/WG/files/PorozoffVPN-{self.s_id}-{self.chat_id}.conf'

        # Сохраняем конфигурационный файл
        async with aiofiles.open(file_path, 'wb') as f:
            async with client.stream("GET", response_data['url']) as stream:
                async for chunk in stream.aiter_bytes():
                    await f.write(chunk)

        # Обновляем информацию о сервере
        await server_space_update(f"WG_{self.s_id}", response_data['space'])
        return file_path

    async def _delete_user_from_server(self, client: httpx.AsyncClient, server_url: str,server_id: int):
        """
        Удаляет пользователя с сервера.

        :param client: Асинхронный клиент httpx.
        :param server_url: URL сервера для удаления пользователя.
        """
        try:
            url = server_url + "/deleteWG"
            data = {"chat_id": self.chat_id}
            response = await client.post(url, json=data)
            response.raise_for_status()
            response_data = response.json()
            await server_space_update(f"WG_{server_id}", response_data['space'])
            logging.info(f"User {self.chat_id} removed from server {server_url}")
        except httpx.RequestError as e:
            logging.error(f"Failed to remove user from {server_url}: {e}")
