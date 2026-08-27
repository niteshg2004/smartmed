"""
The predictions app deliberately has no models of its own in Phase 1: it
reads from inventory.InventoryHistory as its training signal and writes
nothing back to the relational database — trained models are serialized to
disk (ml/models/) and loaded at request time. See ml/train.py and
ml/predict.py, added in Phase 5.

If we later want to cache/audit individual predictions, a
PredictionLog(pharmacy, medicine, predicted_at, result_json) model would go
here — intentionally deferred until the ML pipeline exists to populate it.
"""
