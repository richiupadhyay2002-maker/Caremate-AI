import "@/styles/globals.css";
import { AuthProvider } from "@/lib/auth-context";
import AppLayout from "@/components/AppLayout";

export const metadata = {
  title: "Caremate AI — Clinical Decision Support",
  description: "Safety-checked, provider-agnostic RAG and agent pipeline for healthcare",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-clinical-bg antialiased">
        <AuthProvider>
          <AppLayout>{children}</AppLayout>
        </AuthProvider>
      </body>
    </html>
  );
}
