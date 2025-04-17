/**
 * Toast Notification Hook
 * 
 * This file provides a simple API for creating toast notifications.
 * It wraps the primitive toast implementation with a more user-friendly interface.
 */
import { Toast, ToastActionElement, ToastProps } from "@/components/ui/toast"
import {
  useToast as useToastBase,
  ToastActionType,
} from "@/components/ui/use-toast-primitive"

/**
 * Options for creating a toast notification
 */
type ToastOptions = Omit<
  ToastProps,
  "id" | "title" | "description" | "action" | "className"
> & {
  title?: React.ReactNode
  description?: React.ReactNode
  action?: ToastActionElement
  variant?: "default" | "destructive" | "success"
}

// Re-export the primitive hook
export const useToast = useToastBase

/**
 * Create a toast notification
 * 
 * @example
 * toast({
 *   title: "Success",
 *   description: "Your action was completed",
 *   variant: "success"
 * });
 * 
 * @param opts Toast configuration options
 */
export function toast(opts: ToastOptions) {
  const { toast } = useToastBase()
  return toast(opts)
} 