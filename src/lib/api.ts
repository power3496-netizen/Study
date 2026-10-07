export const api = (path: string, init?: RequestInit) => {
  const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const cleanPath = path.replace(/^\/+/, '');
  const cleanBase = backendUrl.replace(/\/+$/, '');

  // 이 부분이 꼭 있어야 백엔드가 로그인을 인정해 줍니다!
  const userPin = localStorage.getItem('study_user_pin') || '0000';

  return fetch(`${cleanBase}/api/${cleanPath}`, {
    ...init,
    headers: {
      ...init?.headers,
      'X-Study-User': userPin,
    },
  });
}
