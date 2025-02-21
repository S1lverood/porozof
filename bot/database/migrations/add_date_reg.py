from datetime import datetime
from sqlalchemy import text
from bot.database.main import engine

async def migrate():
    """Add date_reg column to users table"""
    async with engine().begin() as conn:
        # Check if column exists
        check_column = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='date_reg';
        """
        result = await conn.execute(text(check_column))
        column_exists = result.scalar() is not None
        
        if not column_exists:
            # Add column
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN date_reg TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            )
            # Set default value for existing rows
            await conn.execute(
                text("UPDATE users SET date_reg = CURRENT_TIMESTAMP WHERE date_reg IS NULL")
            )
