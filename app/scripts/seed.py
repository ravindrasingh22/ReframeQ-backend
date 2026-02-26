import json
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db.init_db import init_db
from app.db.session import SessionLocal

from app.models import AnalyticsEvent, AuditLog, GuardianLink, Journey, PlatformSetting, Profile, User, UserDetail


def seed() -> None:
    init_db()

    db = SessionLocal()
    try:
        db.execute(delete(AuditLog))
        db.execute(delete(AnalyticsEvent))
        db.execute(delete(GuardianLink))
        db.execute(delete(Profile))
        db.execute(delete(UserDetail))
        db.execute(delete(PlatformSetting))
        db.execute(delete(Journey))
        db.execute(delete(User))

        users = [
            User(email='admin@admin.reframeq.local', password_hash='placeholder', role='admin', is_active=True),
            User(email='editor@editor.reframeq.local', password_hash='placeholder', role='content_editor', is_active=True),
            User(email='support@support.reframeq.local', password_hash='placeholder', role='support', is_active=True),
            User(email='analyst@analyst.reframeq.local', password_hash='placeholder', role='analyst', is_active=True),
            User(email='maya@example.com', password_hash='placeholder', role='app_user', is_active=True),
            User(email='arjun@example.com', password_hash='placeholder', role='app_user', is_active=True),
            User(email='leah@example.com', password_hash='placeholder', role='app_user', is_active=True),
        ]
        db.add_all(users)
        db.flush()

        user_details = [
            UserDetail(
                user_id=user.id,
                full_name=user.email.split('@')[0].replace('.', ' ').title(),
                country='India',
                language='en',
            )
            for user in users
        ]
        db.add_all(user_details)
        db.add(
            PlatformSetting(
                key='supported_languages',
                value_json=json.dumps([{'code': 'en', 'name': 'English', 'enabled': True}]),
            )
        )

        adults = [
            Profile(user_id=users[4].id, profile_type='adult', display_name='Maya', age_band='adult', is_active=True),
            Profile(user_id=users[6].id, profile_type='adult', display_name='Leah', age_band='adult', is_active=True),
        ]
        db.add_all(adults)
        db.flush()

        child_profiles = [
            Profile(user_id=users[4].id, profile_type='child', display_name='Arjun', age_band='13_15', is_active=True),
            Profile(user_id=users[6].id, profile_type='child', display_name='Noah', age_band='9_12', is_active=False),
        ]
        db.add_all(child_profiles)
        db.flush()

        guardian_links = [
            GuardianLink(
                guardian_user_id=users[4].id,
                child_profile_id=child_profiles[0].id,
                consent_granted=True,
                consent_text_version='v1',
                consented_at=datetime.now(timezone.utc),
                daily_time_limit_minutes=60,
                topic_restrictions_json=json.dumps(['adult_relationships']),
                conversation_visibility_rule='summary_only',
            ),
            GuardianLink(
                guardian_user_id=users[6].id,
                child_profile_id=child_profiles[1].id,
                consent_granted=False,
                consent_text_version='pending',
                consented_at=None,
                daily_time_limit_minutes=45,
                topic_restrictions_json=json.dumps(['explicit_content', 'self-harm-detailed']),
                conversation_visibility_rule='titles_only',
            ),
        ]
        db.add_all(guardian_links)

        journeys = [
            Journey(
                title='Overthinking Reset',
                topic='Overthinking',
                difficulty='beginner',
                is_published=True,
                summary='A short guided journey to challenge repetitive thought loops.'
            ),
            Journey(
                title='Social Confidence Builder',
                topic='Confidence',
                difficulty='intermediate',
                is_published=True,
                summary='Daily confidence ladder practice with reflection prompts.'
            ),
            Journey(
                title='Calm Focus 7-Day',
                topic='Calmness',
                difficulty='beginner',
                is_published=False,
                summary='A draft weekly journey for mindful focus and breathing cadence.'
            ),
        ]
        db.add_all(journeys)

        events = [
            AnalyticsEvent(event_type='dau', value=1248),
            AnalyticsEvent(event_type='journey_completion_rate', value=68),
            AnalyticsEvent(event_type='sensitive_content_detection', value=17),
            AnalyticsEvent(event_type='top_journey', journey_title='Overthinking Reset', value=1),
        ]
        db.add_all(events)

        audit = [
            AuditLog(
                actor_email='admin@admin.reframeq.local',
                action='seed_initialized',
                module='system',
                details='Initial seed loaded for local development with family-child records.'
            )
        ]
        db.add_all(audit)

        db.commit()

        user_count = len(db.execute(select(User)).scalars().all())
        journey_count = len(db.execute(select(Journey)).scalars().all())
        child_count = len(
            db.execute(select(Profile).where(Profile.profile_type == 'child')).scalars().all()
        )
        print(f'Seed complete: users={user_count}, journeys={journey_count}, child_profiles={child_count}')
    finally:
        db.close()


if __name__ == '__main__':
    seed()
