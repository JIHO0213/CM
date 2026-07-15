import { useEffect, useRef, useState } from 'react'
import { loadKakaoMaps } from '../lib/kakaoMapLoader'
import { getCourseColor } from '../lib/courseColors'

// 코스들을 카카오맵 위에 마커+선(Polyline)으로 그려주는 컴포넌트
// courses: [{ places: [{ name, lat, lng }] }, ...]
// activeIndex: 강조해서 보여줄 코스의 순서(0부터 시작). null이면 전체 코스를 다 보여줌
export default function MapView({ courses, activeIndex }) {
  const containerRef = useRef(null) // 지도가 그려질 div
  const mapRef = useRef(null) // 생성된 kakao.maps.Map 인스턴스
  const kakaoRef = useRef(null) // 로딩된 kakao 전역 객체
  const overlaysRef = useRef([]) // 지금까지 그려둔 마커/선 목록 (다시 그릴 때 정리용)

  const [mapReady, setMapReady] = useState(false) // 지도 객체 생성이 끝났는지
  const [error, setError] = useState(null) // 실패했을 때 보여줄 안내 문구

  // 처음 한 번만: SDK를 불러오고 지도 객체를 생성
  useEffect(() => {
    let cancelled = false

    loadKakaoMaps()
      .then((kakao) => {
        if (cancelled || !containerRef.current) return
        try {
          const map = new kakao.maps.Map(containerRef.current, {
            // 임시 중심(서울시청). 아래 두 번째 useEffect에서 실제 장소들에 맞춰 자동으로 조정됨
            center: new kakao.maps.LatLng(37.5665, 126.978),
            level: 6,
          })
          mapRef.current = map
          kakaoRef.current = kakao
          setMapReady(true)
        } catch {
          setError('지도를 불러올 수 없습니다')
        }
      })
      .catch(() => {
        setError('지도를 불러올 수 없습니다')
      })

    return () => {
      cancelled = true
    }
  }, [])

  // 지도가 준비되었거나, 강조할 코스가 바뀌었을 때: 마커+선을 다시 그림
  useEffect(() => {
    if (!mapReady) return

    try {
      const kakao = kakaoRef.current
      const map = mapRef.current

      // 이전에 그려둔 마커/선을 지도에서 제거
      overlaysRef.current.forEach((overlay) => overlay.setMap(null))
      overlaysRef.current = []

      // activeIndex가 있으면 그 코스만, 없으면 전체 코스를 그림
      const targets =
        activeIndex === null
          ? courses.map((course, index) => ({ course, index }))
          : [{ course: courses[activeIndex], index: activeIndex }]

      const bounds = new kakao.maps.LatLngBounds()

      targets.forEach(({ course, index }) => {
        const path = course.places.map((place) => {
          const position = new kakao.maps.LatLng(place.lat, place.lng)
          bounds.extend(position)

          const marker = new kakao.maps.Marker({ position, map })
          overlaysRef.current.push(marker)

          return position
        })

        const polyline = new kakao.maps.Polyline({
          path,
          strokeWeight: 4,
          strokeColor: getCourseColor(index),
          strokeOpacity: 0.9,
          strokeStyle: 'solid',
        })
        polyline.setMap(map)
        overlaysRef.current.push(polyline)
      })

      // 마커들이 전부 보이도록 지도 중심/줌을 자동 조정
      if (!bounds.isEmpty()) {
        map.setBounds(bounds)
      }
    } catch {
      setError('지도를 표시하는 중 문제가 발생했습니다')
    }
  }, [mapReady, activeIndex, courses])

  if (error) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-100">
        <div className="text-center">
          <p className="text-2xl">🗺️</p>
          <p className="mt-2 text-sm text-gray-500">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative h-56 w-full overflow-hidden rounded-xl border border-gray-200">
      {!mapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <p className="text-sm text-gray-400">지도를 불러오는 중...</p>
        </div>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  )
}
