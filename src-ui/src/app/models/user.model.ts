export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser?: boolean;
  date_joined: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user_id: number;
  username: string;
  email: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface RegisterResponse {
  token: string;
  user_id: number;
  username: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}
