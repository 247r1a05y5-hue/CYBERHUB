export interface Case {
  id: string;
  case_number: string;
  title: string;
  description?: string | null;
  target_subject_label?: string | null;
  status: string;
  current_stage: number;
  created_at: string;
  updated_at?: string;
}
