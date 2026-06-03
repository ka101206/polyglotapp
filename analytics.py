from datetime import date
from sqlalchemy.orm import Session
from database import Analytic, User

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

    def get_summary(self):
        records = self.db.query(Analytic).filter(Analytic.user_id == self.user_id).order_by(Analytic.date).all()
        if not records:
            return None
        
        total_time = sum(r.total_speaking_time for r in records)
        total_mistakes = sum(r.mistakes_count for r in records)
        
        sum_fluency = sum(r.sum_fluency_score for r in records)
        count_fluency = sum(r.count_fluency_score for r in records)
        avg_fluency = sum_fluency / count_fluency if count_fluency > 0 else 0
        
        sum_grammar = sum(r.sum_grammar_score for r in records)
        count_grammar = sum(r.count_grammar_score for r in records)
        avg_grammar = sum_grammar / count_grammar if count_grammar > 0 else 0
        
        sum_listening = sum(r.sum_listening_score for r in records)
        count_listening = sum(r.count_listening_score for r in records)
        avg_listening = sum_listening / count_listening if count_listening > 0 else 0
        
        return {
            "total_speaking_time_minutes": round(total_time / 60, 1),
            "total_mistakes": total_mistakes,
            "avg_fluency_score": round(avg_fluency, 1),
            "avg_grammar_score": round(avg_grammar, 1),
            "avg_listening_score": round(avg_listening, 1)
        }
