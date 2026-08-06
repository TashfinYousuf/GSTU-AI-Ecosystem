import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from 'react-hot-toast';
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: 'GSTU AI: Ultimate Ecosystem',
  description: 'The centralized intelligence hub for International Relations, GSTU.',
  icons: {
    icon: '/logo.png', // 🔴 Webpage Tab Logo
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}
        {/* Global Premium Toast Notification */}
          <Toaster 
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#333',
                color: '#fff',
                borderRadius: '10px',
                border: '1px solid #444',
              },
              success: {
                iconTheme: { primary: '#4ade80', secondary: '#fff' },
              },
            }}
          />
      </body>
    </html>
  );
}
