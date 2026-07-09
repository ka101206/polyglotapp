from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from database import Analytic, User, WeakPoint

class AnalyticsManager:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _get_today_analytic(self) -> Analytic:
        today = date.today()
        record = self.db.query(Analytic).filter(Analytic.user_id == self.user_id, Analytic.date == today).first()
        if not record:
            record = Analytic(user_id=self.user_id, date=today)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        return record

    def add_speaking_time(self, duration_seconds: float):
        record = self._get_today_analytic()
        record.total_speaking_time += duration_seconds
        self.db.commit()

    def add_mistake(self):
        record = self._get_today_analytic()
        record.mistakes_count += 1
        self.db.commit()

    def add_grammar_score(self, score: float):
        record = self._get_today_analytic()
        record.sum_grammar_score += score
        record.count_grammar_score += 1
        self.db.commit()

    def add_fluency_score(self, score: float):
        record = self._get_today_analytic()
        record.sum_fluency_score += score
        record.count_fluency_score += 1
        self.db.commit()

    def add_listening_score(self, score: float):
        record = self._get_today_analytic()
        record.sum_listening_score += score
        record.count_listening_score += 1
        self.db.commit()

    def add_pronunciation_score(self, score: float):
        record = self._get_today_analytic()
        record.sum_pronunciation_score += score
        record.count_pronunciation_score += 1
        self.db.commit()

    # --- Fluency sub-stats ---
    def add_confidence_score(self, score: float):
        record = self._get_today_analytic()
        record.sum_confidence_score += score
        record.count_confidence_score += 1
        self.db.commit()

    def add_flow_score(self, score: float):
        record = self._get_today_analytic()
        record.sum_flow_score += score
        record.count_flow_score += 1
        self.db.commit()

    # --- Weak points (aggregated counters) ---
    def record_weak_point(self, category: str, key: str, score: float = 0.0):
        """Upsert a weak-point counter. category: 'grammar'|'flow'|'confidence'."""
        if not key:
            return
        key = str(key).strip()[:200]
        if not key:
            return
        wp = self.db.query(WeakPoint).filter(
            WeakPoint.user_id == self.user_id,
            WeakPoint.category == category,
            WeakPoint.key == key,
        ).first()
        if wp:
            wp.count += 1
            wp.sum_score += score
            wp.last_seen = datetime.utcnow()
        else:
            wp = WeakPoint(user_id=self.user_id, category=category, key=key,
                           count=1, sum_score=score, last_seen=datetime.utcnow())
            self.db.add(wp)
        self.db.commit()

    def get_weak_points(self, category: str, limit: int = 5):
        rows = (self.db.query(WeakPoint)
                .filter(WeakPoint.user_id == self.user_id, WeakPoint.category == category)
                .order_by(WeakPoint.count.desc(), WeakPoint.last_seen.desc())
                .limit(limit).all())
        return [{"key": r.key, "count": r.count,
                 "avg_score": round(r.sum_score / r.count, 1) if r.count else 0}
                for r in rows]

    def get_summary(self):
        records = self.db.query(Analytic).filter(Analytic.user_id == self.user_id).order_by(Analytic.date).all()
        if not records:
            return None

        total_time = sum(r.total_speaking_time for r in records)
        total_mistakes = sum(r.mistakes_count for r in records)

        def avg_over(recs, sum_attr, count_attr):
            s = sum(getattr(r, sum_attr) for r in recs)
            c = sum(getattr(r, count_attr) for r in recs)
            return (s / c) if c > 0 else None

        # Fluency = average of the three sub-stats (confidence, flow, grammar),
        # 33.33% each. Sub-stats with no data yet are excluded rather than
        # dragging the average to 0.
        def fluency_subs(recs):
            return {
                "confidence": avg_over(recs, 'sum_confidence_score', 'count_confidence_score'),
                "flow": avg_over(recs, 'sum_flow_score', 'count_flow_score'),
                "grammar": avg_over(recs, 'sum_grammar_score', 'count_grammar_score'),
            }

        def fluency_of(subs):
            vals = [v for v in subs.values() if v is not None]
            return round(sum(vals) / len(vals), 1) if vals else 0

        subs = fluency_subs(records)
        avg_fluency = fluency_of(subs)
        avg_listening = avg_over(records, 'sum_listening_score', 'count_listening_score') or 0

        # Trends: recent 7 days vs previous 7 days
        today = date.today()
        recent_cutoff = today - timedelta(days=7)
        older_cutoff = today - timedelta(days=14)
        recent = [r for r in records if r.date > recent_cutoff]
        older = [r for r in records if older_cutoff < r.date <= recent_cutoff]

        def trend(sum_attr, count_attr):
            r = avg_over(recent, sum_attr, count_attr)
            o = avg_over(older, sum_attr, count_attr)
            return round(r - o, 1) if (r is not None and o is not None) else None

        grammar_trend = trend('sum_grammar_score', 'count_grammar_score')
        recent_fl = fluency_of(fluency_subs(recent))
        older_fl = fluency_of(fluency_subs(older))
        fluency_trend = round(recent_fl - older_fl, 1) if (recent and older) else None

        return {
            "total_speaking_time_minutes": round(total_time / 60, 1),
            "total_mistakes": total_mistakes,
            "avg_fluency_score": avg_fluency,
            "fluency_sub": {
                "confidence": round(subs["confidence"], 1) if subs["confidence"] is not None else 0,
                "flow": round(subs["flow"], 1) if subs["flow"] is not None else 0,
                "grammar": round(subs["grammar"], 1) if subs["grammar"] is not None else 0,
            },
            "avg_grammar_score": round(subs["grammar"], 1) if subs["grammar"] is not None else 0,
            "avg_confidence_score": round(subs["confidence"], 1) if subs["confidence"] is not None else 0,
            "avg_flow_score": round(subs["flow"], 1) if subs["flow"] is not None else 0,
            "avg_listening_score": round(avg_listening, 1),
            "grammar_trend": grammar_trend,
            "fluency_trend": fluency_trend,
            "weak_points": {
                "grammar": self.get_weak_points("grammar"),
                "flow": self.get_weak_points("flow"),
                "confidence": self.get_weak_points("confidence"),
            },
        }
