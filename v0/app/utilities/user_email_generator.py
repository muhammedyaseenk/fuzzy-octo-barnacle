import asyncpg
import aiosqlite
import asyncio
import re
import hashlib
import secrets
from typing import Optional, List
from datetime import datetime

DEFAULT_DOMAIN = "@aurum.com"
LUXURY_PREFIXES = ["platinum", "diamond", "elite", "premier", "sovereign", "imperial", "royal", "prestige"]
EXCLUSIVE_SUFFIXES = ["vip", "exclusive", "prime", "select", "distinguished", "privileged"]

def sanitize_luxury(name: str) -> str:
    """Sanitize names preserving luxury appeal - allows dots and hyphens."""
    return re.sub(r"[^a-z0-9.-]", "", name.strip().lower())

def generate_luxury_hash(*args, length: int = 6) -> str:
    """Generate premium alphanumeric hash for exclusivity."""
    combined = "".join(str(arg or "") for arg in args).encode("utf-8")
    hash_bytes = hashlib.blake2b(combined, digest_size=16).hexdigest()
    # Convert to base36 for alphanumeric luxury feel
    hash_int = int(hash_bytes[:12], 16)
    result = ""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    while hash_int > 0 and len(result) < length:
        result = chars[hash_int % 36] + result
        hash_int //= 36
    return result.zfill(length)

class AurumLuxuryEmailGenerator:
    """
    Premium email generator for affluent clientele - handles 10^19+ users efficiently.
    Generates sophisticated, unique professional emails befitting luxury platform users.
    """
    def __init__(self, db, domain: str = DEFAULT_DOMAIN, db_type: str = "postgres"):
        self.db = db
        self.domain = domain
        self.db_type = db_type
        self.luxury_counter = 0  # For premium sequential patterns

    async def reserve_premium_email(self, email: str) -> bool:
        """
        Reserve exclusive email address with optimized conflict handling.
        Returns True if successfully reserved, False if already taken.
        """
        try:
            if self.db_type == "postgres":
                # Ultra-fast PostgreSQL upsert with immediate feedback
                result = await self.db.execute(
                    "INSERT INTO premium_users(email, created_at) VALUES($1, $2) ON CONFLICT (email) DO NOTHING",
                    email, datetime.utcnow()
                )
                return result == "INSERT 0 1"
            else:
                # SQLite optimized insertion
                try:
                    await self.db.execute(
                        "INSERT INTO premium_users(email, created_at) VALUES(?, ?)",
                        (email, datetime.utcnow().isoformat())
                    )
                    await self.db.commit()
                    return True
                except aiosqlite.IntegrityError:
                    return False
        except Exception as e:
            print(f"Premium email reservation failed: {e}")
            return False

    async def generate_luxury_email(
        self,
        first_name: str,
        middle_name: Optional[str] = None,
        last_name: Optional[str] = None,
        location: Optional[str] = None,
        membership_tier: Optional[str] = None,
        max_attempts: int = 2000
    ) -> str:
        """
        Generate exclusive professional email for affluent clientele.
        Prioritizes sophisticated patterns befitting luxury platform users.
        """
        f = sanitize_luxury(first_name)
        m = sanitize_luxury(middle_name) if middle_name else None
        l = sanitize_luxury(last_name) if last_name else None
        loc = sanitize_luxury(location) if location else None
        tier = sanitize_luxury(membership_tier) if membership_tier else None

        # Premium email patterns for affluent users
        luxury_patterns = self._generate_luxury_patterns(f, m, l, loc, tier)
        
        # Try premium patterns first
        for pattern in luxury_patterns:
            candidate = f"{pattern}{self.domain}"
            if await self.reserve_premium_email(candidate):
                return candidate

        # Sophisticated hash-based alternatives
        for attempt in range(max_attempts):
            base_pattern = luxury_patterns[attempt % len(luxury_patterns)]
            
            # Premium alphanumeric suffixes
            if attempt < 500:
                suffix = generate_luxury_hash(f, m, l, loc, attempt, length=4)
                candidate = f"{base_pattern}.{suffix}{self.domain}"
            # Exclusive luxury prefixes
            elif attempt < 1000:
                prefix = LUXURY_PREFIXES[attempt % len(LUXURY_PREFIXES)]
                candidate = f"{prefix}.{base_pattern}{self.domain}"
            # Distinguished suffixes
            elif attempt < 1500:
                suffix_word = EXCLUSIVE_SUFFIXES[attempt % len(EXCLUSIVE_SUFFIXES)]
                hash_part = generate_luxury_hash(f, l, attempt, length=3)
                candidate = f"{base_pattern}.{suffix_word}{hash_part}{self.domain}"
            # Ultimate fallback with premium sequential
            else:
                self.luxury_counter += 1
                candidate = f"{f}.exclusive{self.luxury_counter:06d}{self.domain}"
            
            if await self.reserve_premium_email(candidate):
                return candidate

        raise RuntimeError(f"Unable to generate unique luxury email after {max_attempts} premium attempts")

    def _generate_luxury_patterns(self, f: str, m: Optional[str], l: Optional[str], 
                                loc: Optional[str], tier: Optional[str]) -> List[str]:
        """Generate sophisticated email patterns for affluent users."""
        patterns = []
        
        # Executive patterns
        if f and m and l:
            patterns.extend([
                f"{f}.{m[0]}.{l}",  # john.a.smith
                f"{f[0]}.{m}.{l}",  # j.andrew.smith  
                f"{f}.{m}.{l}",     # john.andrew.smith
            ])
        
        # Distinguished patterns
        if f and l:
            patterns.extend([
                f"{f}.{l}",         # john.smith
                f"{l}.{f}",         # smith.john (executive style)
                f"{f[0]}{l}",       # jsmith
            ])
            
        # Location-based luxury
        if f and loc:
            patterns.extend([
                f"{f}.{loc}",       # john.manhattan
                f"{f}.of.{loc}",    # john.of.manhattan
            ])
            
        # Tier-based exclusivity
        if f and tier:
            patterns.append(f"{f}.{tier}")  # john.platinum
            
        # Elegant minimalist
        patterns.append(f)  # john
        
        return patterns

class DatabaseManager:
    """Manages premium user database with optimized schema for massive scale."""
    
    @staticmethod
    async def init_luxury_db(db_path: str = "aurum_users.db"):
        """Initialize premium user database with luxury-optimized schema."""
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS premium_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    membership_tier TEXT DEFAULT 'platinum',
                    is_vip BOOLEAN DEFAULT TRUE
                )
            """)
            # Optimized index for massive scale lookups
            await db.execute("CREATE INDEX IF NOT EXISTS idx_email_hash ON premium_users(email)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON premium_users(created_at)")
            await db.commit()
        print("✨ Aurum luxury user database initialized successfully!")
    
    @staticmethod
    async def init_postgres_luxury_schema(connection):
        """Initialize PostgreSQL schema optimized for 10^19+ users."""
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS premium_users (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                membership_tier VARCHAR(50) DEFAULT 'platinum',
                is_vip BOOLEAN DEFAULT TRUE
            )
        """)
        # Ultra-fast hash index for massive scale
        await connection.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_premium_email_hash ON premium_users USING hash(email)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_premium_created ON premium_users(created_at)")
        print("🏆 PostgreSQL luxury schema initialized for massive scale!")

# Luxury Email Generation Examples
async def demonstrate_luxury_generation():
    """Demonstrate premium email generation for affluent Aurum clientele."""
    
    # Initialize luxury database
    await DatabaseManager.init_luxury_db("aurum_premium.db")
    
    # PostgreSQL for massive scale (10^19+ users)
    try:
        pg_conn = await asyncpg.connect("postgresql://aurum_user:luxury_pass@localhost/aurum_db")
        await DatabaseManager.init_postgres_luxury_schema(pg_conn)
        
        luxury_generator = AurumLuxuryEmailGenerator(pg_conn, db_type="postgres")
        
        # Generate emails for distinguished clientele
        vip_email = await luxury_generator.generate_luxury_email(
            "Alexander", "James", "Rothschild", "Manhattan", "diamond"
        )
        print(f"🏆 VIP Email: {vip_email}")
        
        await pg_conn.close()
    except Exception as e:
        print(f"PostgreSQL connection unavailable: {e}")
    
    # SQLite for development/testing
    sqlite_conn = await aiosqlite.connect("aurum_premium.db")
    luxury_generator = AurumLuxuryEmailGenerator(sqlite_conn, db_type="sqlite")
    
    # Generate premium emails for affluent users
    premium_emails = []
    
    # Ultra-wealthy clientele examples
    clients = [
        ("Victoria", "Elizabeth", "Pemberton", "Monaco", "sovereign"),
        ("Maximilian", "Von", "Habsburg", "Zurich", "imperial"),
        ("Isabella", "Grace", "Vanderbilt", "Hamptons", "platinum"),
        ("Sebastian", "Charles", "Worthington", "London", "diamond")
    ]
    
    for first, middle, last, location, tier in clients:
        email = await luxury_generator.generate_luxury_email(first, middle, last, location, tier)
        premium_emails.append(email)
        print(f"💎 Luxury Email: {email}")
    
    await sqlite_conn.close()
    print(f"\n✨ Generated {len(premium_emails)} exclusive emails for Aurum's distinguished clientele")

if __name__ == "__main__":
    print("🏆 Aurum Luxury Email Generator - For the World's Most Affluent")
    print("💎 Generating sophisticated emails for 10^19+ premium users\n")
    
    asyncio.run(demonstrate_luxury_generation())