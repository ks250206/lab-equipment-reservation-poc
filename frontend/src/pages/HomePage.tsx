import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">室内装置予約システム（PoC）</h1>
      <p className="max-w-2xl text-zinc-700">
        研究室の共有装置を検索し、ログイン後に時間帯を指定して予約できます。装置の閲覧はログインなしでも行えます。
      </p>
      <ul className="list-inside list-disc text-blue-800">
        <li>
          <Link to="/devices" className="underline">
            装置を探す
          </Link>
        </li>
        <li>
          <Link to="/reservations" className="underline">
            予約を管理する
          </Link>{" "}
          <span className="text-zinc-600">（要ログイン）</span>
        </li>
      </ul>
    </div>
  );
}
