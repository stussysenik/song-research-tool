/**
 * Root Layout Component
 * 
 * This is the main layout wrapper for the entire application.
 * It includes global styles, fonts, and UI components that should appear on every page.
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

// Load the Inter font
const inter = Inter({ subsets: ["latin"] });

// Define page metadata
export const metadata: Metadata = {
  title: "Valentine's Playlist Downloader",
  description: "Extract songs from images and download them as MP3s",
};

/**
 * Root layout component that wraps all pages
 * 
 * @param children The page content to render
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        {children}
        <Toaster /> {/* Global toast notifications */}
      </body>
    </html>
  );
}
