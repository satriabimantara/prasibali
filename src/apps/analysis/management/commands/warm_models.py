"""Download (first run) and load the default models: SatuaNER, label encoder, default classifier, FastText (TF5).

Run once when the container starts, so the Hugging Face cache (HF_HOME) is filled before HF_HUB_OFFLINE=1 and the
first request does not wait for the embedding.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.analysis.services import embeddings, model_registry
from apps.analysis.services.exceptions import AnalysisError


class Command(BaseCommand):
    help = "Load the default AI models (and download the FastText embedding on first use)."

    def add_arguments(self, parser):
        parser.add_argument("--skip-embedding", action="store_true", help="do not load the FastText embedding (TF5)")

    def handle(self, *args, **options):
        include_embedding = not options["skip_embedding"]
        if include_embedding:
            source = embeddings.embedding_source()
            where = source.path if source.kind == "local" else f"Hugging Face {source.repo_id}"
            self.stdout.write(f"FastText (TF5): {source.filename} from {where}")
        try:
            timings = model_registry.warm_up(include_embedding=include_embedding, log=self.stdout.write)
        except AnalysisError as exc:
            raise CommandError(f"Model warm-up failed: {exc.detail or exc}") from exc
        if include_embedding and embeddings.is_loaded():
            size = getattr(embeddings.load_fasttext(), "vector_size", "?")
            self.stdout.write(f"FastText vector_size: {size}")
        self.stdout.write(self.style.SUCCESS(f"Models ready in {sum(timings.values()):.1f}s"))
