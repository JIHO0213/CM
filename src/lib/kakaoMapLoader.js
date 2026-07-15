// 카카오맵 JS SDK 스크립트를 불러오는 함수
// 채팅 메시지마다 지도가 하나씩 생기므로, 스크립트는 딱 한 번만 불러오고
// 이후 호출들은 같은 Promise를 재사용하도록 만들었음 (중복 로딩 방지)
let loadPromise = null

export function loadKakaoMaps() {
  if (loadPromise) return loadPromise

  loadPromise = new Promise((resolve, reject) => {
    const appKey = import.meta.env.VITE_KAKAO_MAP_KEY

    if (!appKey) {
      loadPromise = null // 다음 시도 때 다시 확인할 수 있게 초기화 (키를 나중에 추가하는 경우 대비)
      reject(new Error('카카오맵 API 키가 없어요 (.env의 VITE_KAKAO_MAP_KEY를 확인해주세요)'))
      return
    }

    // 이미 다른 지도에서 로딩이 끝난 상태라면 바로 재사용
    if (window.kakao && window.kakao.maps) {
      resolve(window.kakao)
      return
    }

    const script = document.createElement('script')
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&autoload=false`
    script.async = true
    script.onload = () => {
      // autoload=false로 불러왔기 때문에 직접 load를 호출해야 지도 객체를 쓸 수 있음
      window.kakao.maps.load(() => resolve(window.kakao))
    }
    script.onerror = () => {
      loadPromise = null // 실패하면 다음 시도 때 다시 로딩할 수 있게 초기화 (와이파이 재연결 대비)
      reject(new Error('카카오맵 스크립트를 불러오지 못했어요'))
    }
    document.head.appendChild(script)
  })

  return loadPromise
}
