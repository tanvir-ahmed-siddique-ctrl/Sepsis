import { redirect } from 'next/navigation';

export default function LegacyJudgeRoute() {
  redirect('/system-check');
}
