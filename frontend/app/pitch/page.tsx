import type { Metadata } from 'next';
import PitchClient from './PitchClient';

export const metadata: Metadata = {
  title: 'Pitch Companion • SIH25071',
  description:
    'SIH 2026 master pitch companion and defense rehearsal hub for the AI-Powered Rockfall Early Warning System.',
};

export default function PitchPage() {
  return <PitchClient />;
}
