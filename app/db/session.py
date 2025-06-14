import logging, time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.exercise import Base 
from urllib.parse import quote_plus
from app.core.config import settings

logger = logging.getLogger(__name__)

# DATABASE_URL = (
#     f"mysql+aiomysql://"
#     f"{settings.mysql_user}:{quote_plus(settings.mysql_password)}"
#     f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}"
# )
from sqlalchemy import URL

DATABASE_URL = URL.create(
    "mysql+aiomysql",
    username=settings.mysql_user,
    password=settings.mysql_password,
    host=settings.mysql_host,
    port=settings.mysql_port,
    database=settings.mysql_db,
)
print(DATABASE_URL)

# 1) Khởi tạo engine với try/except
try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        future=True,
    )
    logger.info("Database engine created successfully")
except Exception as e:
    engine = None
    logger.error("Failed to create async engine: %s", e, exc_info=True)

# 2) Tạo sessionmaker (nếu engine là None thì bind=None)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency cho FastAPI hoặc bất kỳ framework nào
async def get_db():
    if engine is None:
        # nếu engine chưa khởi tạo được, chỉ log và yield None
        logger.error("DB engine unavailable, skipping session creation")
        yield None
        return

    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception as e:
        # catch mọi lỗi khi tạo hoặc sử dụng session
        logger.error("Error during DB session: %s", e, exc_info=True)
        # vẫn yield None để downstream không bị crash
        yield None


async def init_db():
    """
    Kiểm tra kết nối và tạo tất cả tables (Base.metadata) nếu chưa tồn tại.
    Gọi hàm này trong startup event của FastAPI hoặc bất kỳ chỗ nào cần migrate.
    """
    if engine is None:
        logger.error("DB engine unavailable, skipping init_db()")
        return

    try:
        async with engine.connect() as conn:
            # 1) Test connection
            await conn.execute(text("SELECT 1"))
            logger.info("✔️  Database connection successful")

            # 2) Tạo bảng
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✔️  All tables created")
    except Exception as e:
        logger.error("❌  init_db failed: %s", e, exc_info=True)
        

async def health_check_db() -> dict:
    """
    Trả về dict chứa trạng thái kết nối và latency của DB.
    """
    status = {"ok": False, "error": None, "latency_ms": None}

    if engine is None:
        status["error"] = "Engine not initialized"
        return status

    start = time.time()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["ok"] = True
    except Exception as e:
        status["error"] = str(e)
    finally:
        status["latency_ms"] = int((time.time() - start) * 1000)

    return status