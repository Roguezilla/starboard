from discpy.discpy import DiscPy, Message

async def is_owner(self: DiscPy, msg: Message):
    return await self.is_owner(msg.author.id)

async def is_mod(self: DiscPy, msg: Message):
    return await self.has_permissions(msg, self.Permissions.MANAGE_MESSAGES) or await self.is_owner(msg.author.id)