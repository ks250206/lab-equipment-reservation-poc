import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { AdminUsersPage } from "@/pages/AdminUsersPage";
import { DeviceDetailPage } from "@/pages/DeviceDetailPage";
import { DevicesPage } from "@/pages/DevicesPage";
import { HomePage } from "@/pages/HomePage";
import { ReservationsPage } from "@/pages/ReservationsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route path="devices/:deviceId" element={<DeviceDetailPage />} />
        <Route path="reservations" element={<ReservationsPage />} />
        <Route path="admin/users" element={<AdminUsersPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
