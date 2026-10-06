export const api = (path: string, init?: RequestInit) => {
  // Vercel에 설정한 환경 변수(VITE_API_URL)를 가져옵니다. 
  // 만약 값이 없다면 로컬 테스트용 localhost를 기본으로 사용합니다.
  const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  // 불필요한 슬래시(/)를 정리하고 최종 주소를 만듭니다.
  const cleanPath = path.replace(/^\/+/, '');
  const cleanBase = backendUrl.replace(/\/+$/, '');

  return fetch(`${cleanBase}/api/${cleanPath}`, init);
}
