export type Device = {
  id: string;
  name: string;
  description: string | null;
  location: string | null;
  category: string | null;
  status: string;
  created_at: string;
  updated_at: string;
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
};

export type UserSelf = {
  id: string;
  email: string;
  name: string | null;
  keycloak_id: string;
  role: string;
  created_at: string;
};

export type FacetsResponse = {
  category: { value: string; count: number }[];
  location: { value: string; count: number }[];
  status: { value: string; count: number }[];
};
