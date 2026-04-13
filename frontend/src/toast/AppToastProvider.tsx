import * as Toast from "@radix-ui/react-toast";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

type ToastContextValue = (message: string) => void;

const ToastContext = createContext<ToastContextValue>(() => {});

export function useAppToast(): ToastContextValue {
  return useContext(ToastContext);
}

export function AppToastProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [payload, setPayload] = useState({ id: 0, message: "" });

  const show = useCallback((text: string) => {
    setPayload((p) => ({ id: p.id + 1, message: text }));
    setOpen(true);
  }, []);

  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      <Toast.Provider duration={4500} swipeDirection="right">
        {children}
        <Toast.Root
          key={payload.id}
          open={open}
          onOpenChange={setOpen}
          className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-900 shadow-lg"
        >
          <Toast.Title className="font-medium">{payload.message}</Toast.Title>
        </Toast.Root>
        <Toast.Viewport className="fixed right-4 bottom-4 z-[100] flex w-[min(100vw-2rem,22rem)] flex-col gap-2 outline-none" />
      </Toast.Provider>
    </ToastContext.Provider>
  );
}
