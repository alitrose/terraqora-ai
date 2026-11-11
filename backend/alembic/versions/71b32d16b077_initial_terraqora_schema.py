"""initial_terraqora_schema

Revision ID: 71b32d16b077
Revises:
Create Date: 2026-11-11 22:54:53.245193
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "71b32d16b077"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_variant() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="farmer", nullable=False),
        sa.Column("preferred_language", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("preferred_language IN ('en', 'ta', 'ml', 'hi', 'te')", name="ck_users_preferred_language"),
        sa.CheckConstraint("role IN ('farmer', 'admin')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index("ix_users_role", ["role"], unique=False)

    op.create_table(
        "farmer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("phone", sa.String(length=24), nullable=True),
        sa.Column("state", sa.String(length=80), nullable=True),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("primary_soil_type", sa.String(length=60), nullable=True),
        sa.Column("preferred_units", sa.String(length=20), server_default="metric", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("preferred_units IN ('metric', 'imperial')", name="ck_farmer_profiles_preferred_units"),
        sa.CheckConstraint("experience_years IS NULL OR experience_years >= 0", name="ck_farmer_profiles_experience_years"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "farms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("area_hectares", sa.Double(), nullable=False),
        sa.Column("soil_type", sa.String(length=60), nullable=True),
        sa.Column("soil_ph", sa.Double(), nullable=True),
        sa.Column("irrigation_type", sa.String(length=40), nullable=True),
        sa.Column("primary_crop", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "irrigation_type IS NULL OR irrigation_type IN ('rainfed', 'drip', 'sprinkler', 'canal', 'borewell', 'mixed')",
            name="ck_farms_irrigation_type",
        ),
        sa.CheckConstraint("area_hectares > 0", name="ck_farms_area_positive"),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_farms_latitude"),
        sa.CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_farms_longitude"),
        sa.CheckConstraint("soil_ph IS NULL OR (soil_ph >= 0 AND soil_ph <= 14)", name="ck_farms_soil_ph"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("farms", schema=None) as batch_op:
        batch_op.create_index("ix_farms_state", ["state"], unique=False)
        batch_op.create_index("ix_farms_user_id", ["user_id"], unique=False)

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), server_default="New Farming Consultation", nullable=False),
        sa.Column("language", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("language IN ('en', 'ta', 'ml', 'hi', 'te')", name="ck_cs_lang"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("chat_sessions", schema=None) as batch_op:
        batch_op.create_index("ix_chat_sessions_user_updated", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "crop_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("crop", sa.String(length=80), nullable=False),
        sa.Column("crop_year", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("area_hectares", sa.Double(), nullable=False),
        sa.Column("annual_rainfall_mm", sa.Double(), nullable=False),
        sa.Column("fertilizer_kg", sa.Double(), nullable=False),
        sa.Column("pesticide_kg", sa.Double(), nullable=False),
        sa.Column("predicted_yield", sa.Double(), nullable=False),
        sa.Column("yield_unit", sa.String(length=32), server_default="tonnes/hectare", nullable=False),
        sa.Column("estimated_total_production", sa.Double(), nullable=True),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("feature_importance_json", _json_variant(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("annual_rainfall_mm >= 0", name="ck_cp_rain"),
        sa.CheckConstraint("area_hectares > 0", name="ck_cp_area"),
        sa.CheckConstraint("crop_year >= 1990 AND crop_year <= 2100", name="ck_cp_year"),
        sa.CheckConstraint("fertilizer_kg >= 0", name="ck_cp_fert"),
        sa.CheckConstraint("pesticide_kg >= 0", name="ck_cp_pest"),
        sa.CheckConstraint("predicted_yield >= 0", name="ck_cp_yield"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("crop_predictions", schema=None) as batch_op:
        batch_op.create_index("ix_crop_predictions_crop_state", ["crop", "state"], unique=False)
        batch_op.create_index("ix_crop_predictions_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "crop_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("nitrogen", sa.Double(), nullable=False),
        sa.Column("phosphorus", sa.Double(), nullable=False),
        sa.Column("potassium", sa.Double(), nullable=False),
        sa.Column("temperature_c", sa.Double(), nullable=False),
        sa.Column("humidity_pct", sa.Double(), nullable=False),
        sa.Column("soil_ph", sa.Double(), nullable=False),
        sa.Column("rainfall_mm", sa.Double(), nullable=False),
        sa.Column("season", sa.String(length=40), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("recommended_crop", sa.String(length=80), nullable=False),
        sa.Column("top_candidates_json", _json_variant(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("humidity_pct >= 0 AND humidity_pct <= 100", name="ck_cr_hum"),
        sa.CheckConstraint("nitrogen >= 0", name="ck_cr_n"),
        sa.CheckConstraint("phosphorus >= 0", name="ck_cr_p"),
        sa.CheckConstraint("potassium >= 0", name="ck_cr_k"),
        sa.CheckConstraint("rainfall_mm >= 0", name="ck_cr_rain"),
        sa.CheckConstraint("soil_ph >= 0 AND soil_ph <= 14", name="ck_cr_ph"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("crop_recommendations", schema=None) as batch_op:
        batch_op.create_index("ix_crop_recs_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "disease_detections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("crop_hint", sa.String(length=80), nullable=True),
        sa.Column("image_filename", sa.String(length=255), nullable=False),
        sa.Column("image_mime_type", sa.String(length=64), nullable=False),
        sa.Column("image_size_bytes", sa.Integer(), nullable=False),
        sa.Column("image_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("predicted_label", sa.String(length=120), nullable=False),
        sa.Column("confidence", sa.Double(), nullable=False),
        sa.Column("is_uncertain", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("top_predictions_json", _json_variant(), nullable=False),
        sa.Column("treatment_summary", sa.Text(), nullable=False),
        sa.Column("prevention_notes", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_dd_confidence"),
        sa.CheckConstraint("image_size_bytes > 0", name="ck_dd_size"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("disease_detections", schema=None) as batch_op:
        batch_op.create_index("ix_disease_detections_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "fertilizer_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("nitrogen", sa.Double(), nullable=False),
        sa.Column("phosphorus", sa.Double(), nullable=False),
        sa.Column("potassium", sa.Double(), nullable=False),
        sa.Column("soil_ph", sa.Double(), nullable=False),
        sa.Column("soil_type", sa.String(length=60), nullable=False),
        sa.Column("crop_type", sa.String(length=80), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("recommended_fertilizer", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Double(), nullable=True),
        sa.Column("nutrient_status_json", _json_variant(), nullable=False),
        sa.Column("advisory_notes", sa.Text(), nullable=False),
        sa.Column("expert_disclaimer", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_fr_conf"),
        sa.CheckConstraint("nitrogen >= 0", name="ck_fr_n"),
        sa.CheckConstraint("phosphorus >= 0", name="ck_fr_p"),
        sa.CheckConstraint("potassium >= 0", name="ck_fr_k"),
        sa.CheckConstraint("soil_ph >= 0 AND soil_ph <= 14", name="ck_fr_ph"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("fertilizer_recommendations", schema=None) as batch_op:
        batch_op.create_index("ix_fertilizer_recs_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "irrigation_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("location_name", sa.String(length=120), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("crop_type", sa.String(length=80), nullable=False),
        sa.Column("growth_stage", sa.String(length=40), server_default="mid_season", nullable=False),
        sa.Column("weather_provider", sa.String(length=40), nullable=False),
        sa.Column("weather_snapshot_json", _json_variant(), nullable=False),
        sa.Column("forecast_rainfall_7d_mm", sa.Double(), nullable=False),
        sa.Column("estimated_et0_mm", sa.Double(), nullable=False),
        sa.Column("recommended_water_mm", sa.Double(), nullable=False),
        sa.Column("irrigation_urgency", sa.String(length=24), nullable=False),
        sa.Column("is_sensor_backed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("advisory_notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("irrigation_urgency IN ('low', 'moderate', 'high', 'skip_rain_expected')", name="ck_ir_urgency"),
        sa.CheckConstraint("estimated_et0_mm >= 0", name="ck_ir_et0"),
        sa.CheckConstraint("forecast_rainfall_7d_mm >= 0", name="ck_ir_rain"),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_ir_lat"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_ir_lon"),
        sa.CheckConstraint("recommended_water_mm >= 0", name="ck_ir_water"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("irrigation_recommendations", schema=None) as batch_op:
        batch_op.create_index("ix_irrigation_recs_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", _json_variant(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model_name", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_cm_role"),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_cm_latency"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.create_index("ix_chat_messages_session_created", ["session_id", "created_at"], unique=False)

    op.create_table(
        "generated_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("crop_prediction_id", sa.Uuid(), nullable=True),
        sa.Column("fertilizer_recommendation_id", sa.Uuid(), nullable=True),
        sa.Column("irrigation_recommendation_id", sa.Uuid(), nullable=True),
        sa.Column("report_payload_json", _json_variant(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("pdf_filename", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["crop_prediction_id"], ["crop_predictions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fertilizer_recommendation_id"], ["fertilizer_recommendations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["irrigation_recommendation_id"], ["irrigation_recommendations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generated_reports", schema=None) as batch_op:
        batch_op.create_index("ix_generated_reports_user_created", ["user_id", "created_at"], unique=False)

    if op.get_bind().dialect.name == "postgresql":
        op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
        op.execute(
            """
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for table in ("users", "farmer_profiles", "farms", "chat_sessions"):
            op.execute(
                f"""
                CREATE TRIGGER trg_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
                """
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("chat_sessions", "farms", "farmer_profiles", "users"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
        op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    with op.batch_alter_table("generated_reports", schema=None) as batch_op:
        batch_op.drop_index("ix_generated_reports_user_created")

    op.drop_table("generated_reports")
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.drop_index("ix_chat_messages_session_created")

    op.drop_table("chat_messages")
    with op.batch_alter_table("irrigation_recommendations", schema=None) as batch_op:
        batch_op.drop_index("ix_irrigation_recs_user_created")

    op.drop_table("irrigation_recommendations")
    with op.batch_alter_table("fertilizer_recommendations", schema=None) as batch_op:
        batch_op.drop_index("ix_fertilizer_recs_user_created")

    op.drop_table("fertilizer_recommendations")
    with op.batch_alter_table("disease_detections", schema=None) as batch_op:
        batch_op.drop_index("ix_disease_detections_user_created")

    op.drop_table("disease_detections")
    with op.batch_alter_table("crop_recommendations", schema=None) as batch_op:
        batch_op.drop_index("ix_crop_recs_user_created")

    op.drop_table("crop_recommendations")
    with op.batch_alter_table("crop_predictions", schema=None) as batch_op:
        batch_op.drop_index("ix_crop_predictions_user_created")
        batch_op.drop_index("ix_crop_predictions_crop_state")

    op.drop_table("crop_predictions")
    with op.batch_alter_table("chat_sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_chat_sessions_user_updated")

    op.drop_table("chat_sessions")
    with op.batch_alter_table("farms", schema=None) as batch_op:
        batch_op.drop_index("ix_farms_user_id")
        batch_op.drop_index("ix_farms_state")

    op.drop_table("farms")
    op.drop_table("farmer_profiles")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_role")

    op.drop_table("users")
