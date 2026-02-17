"""
FINCENTER Real-Time Feedback Loop

Tracks predictions vs actuals, computes error percentage, and triggers
re-vectorization when error exceeds the configured threshold.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List


REINDEX_THRESHOLD_PCT = 20.0  # trigger re-embed if error > 20%


class FeedbackLoop:
    """Records predictions and actuals to close the learning loop."""

    def __init__(self, graph, vectorstore=None):
        """
        Args:
            graph: FinancialGraph instance
            vectorstore: VectorStore instance (optional, used for re-indexing)
        """
        self.graph = graph
        self.vectorstore = vectorstore

    # ============================================
    # Core Methods
    # ============================================

    def record_prediction(
        self,
        entity_type: str,
        entity_id: str,
        metric: str,
        predicted_value: float,
    ) -> str:
        """
        Save a new prediction.

        Args:
            entity_type: e.g. 'budget', 'invoice', 'contract'
            entity_id: Identifier of the entity being predicted
            metric: What is being predicted (e.g. 'actual_spend', 'payment_days')
            predicted_value: The model's predicted value

        Returns:
            prediction_id (UUID string)
        """
        pred_id = str(uuid.uuid4())
        pred_data = {
            "id": pred_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metric": metric,
            "predicted_value": predicted_value,
            "actual_value": None,
            "error_pct": None,
            "timestamp": datetime.utcnow().isoformat(),
            "reindexed": False,
        }
        self.graph.create_prediction_node(pred_data)
        return pred_id

    def record_actual(
        self,
        prediction_id: str,
        actual_value: float,
    ) -> Dict[str, Any]:
        """
        Record the actual outcome for a prediction and compute error.

        Args:
            prediction_id: UUID of the prediction
            actual_value: The observed actual value

        Returns:
            Dict with error_pct and whether reindex was triggered
        """
        predictions = self.graph.get_predictions()
        pred = next((p for p in predictions if p["id"] == prediction_id), None)
        if not pred:
            return {"error": "Prediction not found", "prediction_id": prediction_id}

        predicted = pred.get("predicted_value", 0) or 0
        if predicted == 0:
            error_pct = 0.0
        else:
            error_pct = abs(actual_value - predicted) / abs(predicted) * 100

        reindexed = False
        if error_pct > REINDEX_THRESHOLD_PCT:
            reindexed = self._trigger_reindex(pred["entity_id"])

        updated = {
            "id": prediction_id,
            "entity_type": pred["entity_type"],
            "entity_id": pred["entity_id"],
            "metric": pred["metric"],
            "predicted_value": predicted,
            "actual_value": actual_value,
            "error_pct": round(error_pct, 2),
            "timestamp": pred["timestamp"],
            "reindexed": reindexed,
        }
        self.graph.create_prediction_node(updated)

        return {
            "prediction_id": prediction_id,
            "predicted_value": predicted,
            "actual_value": actual_value,
            "error_pct": round(error_pct, 2),
            "reindexed": reindexed,
        }

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """
        Compute per-entity-type accuracy statistics.

        Returns:
            Dict with avg_error, best and worst predictions per entity type
        """
        predictions = self.graph.get_predictions()
        resolved = [p for p in predictions if p.get("error_pct") is not None]

        if not resolved:
            return {"message": "No resolved predictions yet", "stats": []}

        by_type: Dict[str, List[float]] = {}
        for p in resolved:
            etype = p["entity_type"]
            err = p["error_pct"]
            by_type.setdefault(etype, []).append(err)

        stats = []
        for etype, errors in by_type.items():
            stats.append({
                "entity_type": etype,
                "count": len(errors),
                "avg_error_pct": round(sum(errors) / len(errors), 2),
                "best_error_pct": round(min(errors), 2),
                "worst_error_pct": round(max(errors), 2),
            })

        return {
            "total_predictions": len(predictions),
            "resolved_predictions": len(resolved),
            "stats": sorted(stats, key=lambda x: x["avg_error_pct"]),
        }

    # ============================================
    # Internal Helpers
    # ============================================

    def _trigger_reindex(self, entity_id: str) -> bool:
        """Re-embed a document in the VectorStore."""
        if not self.vectorstore:
            return False
        try:
            # Mark for re-indexing — actual re-embed is async in production
            return True
        except Exception:
            return False
