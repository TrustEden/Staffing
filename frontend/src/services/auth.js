import api from "./api";

export async function login(email, password) {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);
  params.append("grant_type", "password");

  const response = await api.post("/auth/token", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data;
}

export async function refresh(refreshToken) {
  const response = await api.post("/auth/refresh", { refresh_token: refreshToken });
  return response.data;
}
