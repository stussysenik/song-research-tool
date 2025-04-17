/**
 * Toaster Component
 * 
 * This component renders all active toast notifications.
 * It should be included once in your application layout.
 * 
 * @example
 * // In your layout component:
 * return (
 *   <html>
 *     <body>
 *       {children}
 *       <Toaster />
 *     </body>
 *   </html>
 * );
 */
"use client"

import { useToast } from "@/components/ui/use-toast-primitive"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"

/**
 * Renders all active toast notifications
 */
export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, ...props }) {
        return (
          <Toast key={id} {...props}>
            <div className="grid gap-1">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
} 