export const api = (path: string, init?: RequestInit) => {
  const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const cleanPath = path.replace(/^\/+/, '');
  const cleanBase = backendUrl.replace(/\/+$/, '');

  // 브라우저에 저장된 유저 PIN 번호를 가져옴 (없으면 기본 관리자 '0000' 등 사용)
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
