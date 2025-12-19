import azure.functions as func
import logging
import sys
import os

from smart_data_manager.seed import seed_database

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Azure Function to seed the database.
    Use manually (dev / demo only).
    """

    logging.info("=" * 60)
    logging.info("Seed Function triggered")
    logging.info("=" * 60)

    # Optional safety check
    # confirm = req.params.get("confirm")
    # if confirm != "true":
    #     return func.HttpResponse(
    #         "⚠️ Seeding is destructive.\n"
    #         "Call with ?confirm=true to proceed.",
    #         status_code=400
    #     )

    try:
        logging.info(f"Python version: {sys.version}")
        logging.info(f"Working directory: {os.getcwd()}")

        seed_database()

        logging.info("Database seeding completed successfully")

        return func.HttpResponse(
            "✅ Database seeded successfully",
            status_code=200
        )

    except Exception as e:
        logging.error("Seeding failed", exc_info=True)
        return func.HttpResponse(
            f"❌ Seeding failed: {str(e)}",
            status_code=500
        )
