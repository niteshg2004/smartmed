from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ml.train import train_and_save


class Command(BaseCommand):
    help = "Train the stock-demand prediction model from InventoryHistory data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=str(Path(settings.BASE_DIR) / "ml" / "models"),
            help="Directory where the trained model and metadata files will be saved.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        try:
            result = train_and_save(output_dir=output_dir)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Stock prediction model trained successfully."))
        self.stdout.write(f"Best model: {result.best_model_name}")
        for model_name, metrics in result.metrics.items():
            self.stdout.write(
                f"{model_name}: "
                f"MAE={metrics['mae']:.4f}, "
                f"RMSE={metrics['rmse']:.4f}, "
                f"R²={metrics['r2']:.4f}"
            )
        self.stdout.write(f"Model saved to: {result.model_path}")
        self.stdout.write(f"Metadata saved to: {result.metadata_path}")
