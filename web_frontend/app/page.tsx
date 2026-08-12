import { redirect } from 'next/navigation';

export default function RootHomePage() {
  // 🔴 INSTANT REDIRECT: Users visiting localhost:3000 will instantly land on the dashboard!
  redirect('/dashboard');
}