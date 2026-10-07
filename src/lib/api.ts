export const api = (path: string, init?: RequestInit) => {
  const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const cleanPath = path.replace(/^\/+/, '');
  const cleanBase = backendUrl.replace(/\/+$/, '');

  // 백엔드가 요구하는 네 자리 PIN 번호를 헤더에 자동으로 실어줍니다.
  const userPin = localStorage.getItem('study_user_pin') || '0000';

  const headers = {
    ...init?.headers,
    'X-Study-User': userPin,
  };

  return fetch(`${cleanBase}/api/${cleanPath}`, {
    ...init,
    headers,
  });
}
