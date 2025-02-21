from sqlalchemy import text
from bot.database.main import engine

async def migrate():
    """Add paid field to users table"""
    async_engine = engine()
    async with async_engine.begin() as conn:
        # Add paid column if it doesn't exist
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS paid BOOLEAN DEFAULT FALSE")
        )
        
        # Update existing users who have made payments, only for valid numeric user IDs
        await conn.execute(
            text("""
                UPDATE users 
                SET paid = TRUE 
                WHERE id::integer IN (
                    SELECT DISTINCT user::integer 
                    FROM payments
                    WHERE user ~ '^[0-9]+$'
                )
            """)
        )
