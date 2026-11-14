export interface UserProfile {
  id: string;
  email: string;
  name: string;
  picture: string;
  provider: string;
  created_at: string;
  last_login: string;
}

export interface GoogleAuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}
