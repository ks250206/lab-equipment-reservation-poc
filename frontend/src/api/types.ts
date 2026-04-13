export type PageSize = 20 | 50 | 100;

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type Device = {
  id: string;
  name: string;
  description: string | null;
  location: string | null;
  category: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  has_image: boolean;
  is_favorite?: boolean;
};

export type Reservation = {
  id: string;
  device_id: string;
  user_id: string;
  start_time: string;
  end_time: string;
  purpose: string | null;
  status: string;
  created_at: string;
  user_name?: string | null;
  user_email?: string | null;
};

/** `GET /api/users/me`（DB の紐付け + JWT 由来の表示・ロールラベル） */
export type UserMe = {
  id: string;
  email: string;
  name: string | null;
  keycloak_id: string;
  role: string;
  created_at: string;
};

/** `GET /api/users` 管理者一覧（アプリ DB に保持している列のみ） */
export type UserDirectoryRow = {
  id: string;
  keycloak_id: string;
  created_at: string;
};

export type FacetsResponse = {
  category: { value: string; count: number }[];
  location: { value: string; count: number }[];
  status: { value: string; count: number }[];
};
