const API_BASE = '/api';

export class ApiError extends Error {
  code?: string;

  constructor(
    public status: number,
    message: string,
    code?: string,
  ) {
    super(message);
    this.code = code;
  }
}

type ErrorBody = { detail?: string | { detail?: string; code?: string } };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body != null && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' });
  if (res.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/auth/register')) {
    window.dispatchEvent(new Event('arpw:unauthorized'));
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as ErrorBody;
    const detail = body.detail;
    if (typeof detail === 'string') {
      throw new ApiError(res.status, detail);
    }
    if (detail && typeof detail === 'object') {
      throw new ApiError(res.status, detail.detail || 'Request failed', detail.code);
    }
    throw new ApiError(res.status, 'Request failed');
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export type LlmProvider = 'openai' | 'xai' | 'anthropic';

export type LlmSettings = {
  openai: { configured: boolean; last4: string | null };
  xai: { configured: boolean; last4: string | null };
  anthropic: { configured: boolean; last4: string | null };
  chat_provider: LlmProvider;
  chat_models: Record<string, string>;
};

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  email_confirmed_at: string | null;
  created_at: string;
  needs_email_confirmation?: boolean;
};

export const api = {
  auth: {
    register: (email: string, password: string, full_name: string) =>
      request<User>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name }),
      }),
    login: (email: string, password: string) =>
      request<User>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
    logout: () => request<void>('/auth/logout', { method: 'POST' }),
    me: () => request<User>('/auth/me'),
    resendConfirmation: (email: string) =>
      request<{ detail: string }>('/auth/resend-confirmation', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),
    forgotPassword: (email: string) =>
      request<{ detail: string }>('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),
    resetPassword: (token: string, password: string) =>
      request<User>('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, password }),
      }),
    patchMe: (full_name: string) =>
      request<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ full_name }) }),
  },
  settings: {
    llm: () => request<LlmSettings>('/settings/llm'),
    updateLlm: (body: Record<string, string>) =>
      request<LlmSettings>('/settings/llm', { method: 'PUT', body: JSON.stringify(body) }),
  },
};

export type SourceRole = 'literature' | 'primary';

export type ReferenceFile = {
  file_id: string;
  file_name: string;
  file_size: number;
  source_role: SourceRole;
  status: string;
  chunk_count: number;
  embedding_model: string | null;
  error_message: string | null;
  citation_text: string | null;
  uploaded_at: string;
  updated_at: string;
};

export type ExampleFile = {
  file_id: string;
  file_name: string;
  file_size: number;
  status: string;
  chunk_count: number;
  embedding_model: string | null;
  error_message: string | null;
  uploaded_at: string;
  updated_at: string;
};

async function postFile<T>(path: string, file: File, fields?: Record<string, string>): Promise<T> {
  const fd = new FormData();
  fd.append('file', file);
  if (fields) {
    Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  }
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', body: fd, credentials: 'include' });
  if (res.status === 401) {
    window.dispatchEvent(new Event('arpw:unauthorized'));
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(res.status, typeof body.detail === 'string' ? body.detail : 'Upload failed');
  }
  return res.json() as Promise<T>;
}

export const PAPER_TYPES = [
  'Empirical Study',
  'Literature Review',
  'Theoretical Paper',
  'Case Study',
] as const;
export const PAPER_SECTIONS = [
  'Abstract',
  'Introduction',
  'Literature Review',
  'Methods',
  'Results',
  'Discussion',
  'Conclusion',
  'References',
] as const;
export const CITATION_STYLES = ['APA', 'MLA', 'Chicago'] as const;
export const OUTPUT_FORMATS = ['markdown', 'word'] as const;

export type Paper = {
  paper_id: string;
  title: string;
  content: string;
  sections: string[] | null;
  paper_type: string;
  citation_style: string;
  output_format: string;
  version: number;
  status: string;
  research_prompt: string;
  outline: string;
  attribution: unknown;
  created_at: string;
  reference_count: number;
};

export type Passage = {
  vector_id: string;
  file_id: string;
  chunk_text: string;
  section: string | null;
  source_role: string;
  score: number;
  page: number | null;
  chunk_role: string | null;
  pinned?: boolean;
};

export type Pin = {
  pin_id: string;
  paper_id: string;
  file_id: string;
  vector_id: string;
  target_section: string | null;
  created_at: string;
  file_name: string;
  source_role: string;
  chunk_text: string;
  section: string | null;
  page: number | null;
  chunk_role: string | null;
};

export const papersApi = {
  list: () => request<Paper[]>('/papers'),
  create: (title: string, paper_type: string) =>
    request<Paper>('/papers', { method: 'POST', body: JSON.stringify({ title, paper_type }) }),
  get: (id: string) => request<Paper>(`/papers/${id}`),
  patch: (id: string, body: Record<string, unknown>) =>
    request<Paper>(`/papers/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  remove: (id: string) => request<void>(`/papers/${id}`, { method: 'DELETE' }),
  regenerate: (id: string) => request<Paper>(`/papers/${id}/regenerate`, { method: 'POST' }),
  retrieve: (id: string, body: { research_prompt: string; paper_type: string; sections?: string[] }) =>
    request<{ passages: Passage[] }>(`/papers/${id}/retrieve`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listPins: (id: string) => request<Pin[]>(`/papers/${id}/pins`),
  pin: (id: string, body: { vector_id: string; file_id: string; target_section?: string | null }) =>
    request<Pin>(`/papers/${id}/pins`, { method: 'POST', body: JSON.stringify(body) }),
  unpin: (id: string, pinId: string) => request<void>(`/papers/${id}/pins/${pinId}`, { method: 'DELETE' }),
  interrogation: (id: string) =>
    request<Array<{ turn_id: string; role: string; content: string; passages: Passage[]; created_at: string }>>(
      `/papers/${id}/interrogation`,
    ),
  ask: (id: string, question: string, sources: string[]) =>
    request<{ answer: string; passages: Passage[]; sources: string[] }>(`/papers/${id}/interrogation`, {
      method: 'POST',
      body: JSON.stringify({ question, sources }),
    }),
  outline: (id: string, body: { paper_type: string; sections: string[]; research_prompt: string }) =>
    request<{ outline: string }>(`/papers/${id}/outline`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  generate: (
    id: string,
    body: {
      paper_type: string;
      sections: string[];
      research_prompt: string;
      citation_style?: string;
      output_format?: string;
    },
  ) =>
    request<{
      paper: Paper;
      sections: Array<{ name: string; text: string }>;
      warnings: Array<{ kind: string; message: string }>;
      disclaimer: string;
      citation_check: { ok: boolean };
      format_check: { ok: boolean };
    }>(`/papers/${id}/generate`, { method: 'POST', body: JSON.stringify(body) }),
};

export const documentsApi = {
  listReferences: () => request<ReferenceFile[]>('/references'),
  uploadReference: (file: File, sourceRole: SourceRole) =>
    postFile<ReferenceFile>('/references', file, { source_role: sourceRole }),
  deleteReference: (id: string) => request<void>(`/references/${id}`, { method: 'DELETE' }),
  patchReference: (id: string, body: { source_role?: SourceRole; citation_text?: string }) =>
    request<ReferenceFile>(`/references/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  lookupCitation: (file_id: string, doi?: string) =>
    request<ReferenceFile>('/citations/lookup', {
      method: 'POST',
      body: JSON.stringify({ file_id, doi: doi || null }),
    }),
  listExamples: () => request<ExampleFile[]>('/examples'),
  uploadExample: (file: File) => postFile<ExampleFile>('/examples', file),
  deleteExample: (id: string) => request<void>(`/examples/${id}`, { method: 'DELETE' }),
};
