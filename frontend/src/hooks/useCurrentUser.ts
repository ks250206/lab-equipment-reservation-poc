import { useQuery } from "@tanstack/react-query";

import { fetchCurrentUser } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

/** ログイン中のみ `/api/users/me` を取得する。 */
export function useCurrentUser() {
  const { authenticated, ready, getValidToken } = useAuth();

  return useQuery({
    queryKey: ["users-me"],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) {
        throw new Error(
          "アクセストークンを取得できませんでした。再ログインするか、ブラウザの Cookie / トラッキング防止設定を確認してください。",
        );
      }
      return fetchCurrentUser(token);
    },
    enabled: Boolean(authenticated && ready),
  });
}
