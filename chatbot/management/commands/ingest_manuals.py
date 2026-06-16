from django.core.management.base import BaseCommand
from chatbot.rag.ingest import ingest


class Command(BaseCommand):
    help = "Ingest service manuals (PDFs) into the ChromaDB vectorstore"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting manual ingestion...")
        ingest()
        self.stdout.write(self.style.SUCCESS("Ingestion complete."))
