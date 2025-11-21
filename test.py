import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test():
    logger.info("=== INICIANDO PRUEBA ===")
    
    # Test 1: Variables de entorno
    logger.info(f"PORT: {os.getenv('PORT')}")
    logger.info(f"DB_HOST: {os.getenv('DB_HOST')}")
    logger.info(f"DB_NAME: {os.getenv('DB_NAME')}")
    
    # Test 2: Importaciones
    try:
        from main import app
        logger.info("✅ FastAPI app importada correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error importando app: {e}")
        return False

if __name__ == "__main__":
    test()