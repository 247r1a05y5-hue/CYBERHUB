/**
 * Types for the Controlled Dataset / AWS Rekognition pipeline.
 * Privacy: no type should include storage_key, raw image URL, or image bytes.
 */

export type ConsentStatus = "PENDING" | "CONSENTED" | "REVOKED" | "EXPIRED";
export type ImageIndexStatus = "PENDING" | "INDEXED" | "FAILED" | "DUPLICATE";
export type MatchStatus = "PENDING_REVIEW" | "VERIFIED" | "REJECTED" | "UNCERTAIN";
export type VerificationStatus = "PENDING_REVIEW" | "VERIFIED" | "REJECTED" | "UNCERTAIN";
export type Platform = "instagram" | "linkedin" | "facebook" | "twitter" | "tiktok" | "youtube" | "other";

export interface Participant {
  id: string;
  organization_id: string;
  participant_code: string;
  display_name: string;
  consent_status: ConsentStatus;
  consent_timestamp: string | null;
  is_active: boolean;
  notes?: string | null;
}

/** Image metadata — never includes storage_key */
export interface ParticipantImage {
  id: string;
  participant_id: string;
  mime_type: string;
  file_size_bytes: number;
  width: number | null;
  height: number | null;
  sha256: string;
  phash: string | null;
  dhash: string | null;
  aws_face_id: string | null;
  aws_external_image_id: string | null;
  index_status: ImageIndexStatus;
  index_error: string | null;
  aws_indexed_at: string | null;
  face_confidence: number | null;
  image_sequence: number;
}

export interface ParticipantPublicSource {
  id: string;
  participant_id: string;
  platform: Platform;
  url: string;
  participant_confirmed: boolean;
}

export interface DatasetStats {
  participant_count: number;
  image_count: number;
  indexed_face_count: number;
  source_count: number;
  consent_pending_count: number;
  last_match_at: string | null;
  aws_configured: boolean;
}

/** Match result — never includes participant photo */
export interface MatchCandidate {
  match_id: string;
  participant_id: string;
  participant_code: string;
  display_name: string;
  aws_similarity: number;
  aws_face_id: string;
  aws_external_image_id: string;
  match_status: MatchStatus;
  matched_at: string;
  public_sources: Array<{ platform: string; url: string }>;
  /** Local secondary similarity — NEVER blended with aws_similarity */
  local_similarity?: number | null;
  local_match_method?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface DatasetVerification {
  id: string;
  match_id: string;
  organization_id: string;
  status: VerificationStatus;
  verified_by: string | null;
  verified_at: string | null;
  verification_note: string | null;
}
