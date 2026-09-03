// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

// One small glyph per method, drawn from the mark's own motif — lines that
// meet a reading. Monochrome, stroke-only, currentColor, so they sit in ink
// beside a title and in muted grey in a list. 24-unit box.

const STROKE = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const,
                 strokeLinejoin: 'round' as const }

const PATHS: Record<string, React.ReactNode> = {
  // grounded theory: many lines converging on one core
  grounded_theory: <>
    <line x1="3" y1="5" x2="13" y2="12" /><line x1="3" y1="12" x2="13" y2="12" />
    <line x1="3" y1="19" x2="13" y2="12" /><circle cx="18" cy="12" r="2.6" />
  </>,
  // thematic analysis: lines gathered into two themes
  thematic: <>
    <line x1="4" y1="6" x2="12" y2="6" /><line x1="4" y1="10" x2="12" y2="10" />
    <line x1="4" y1="16" x2="12" y2="16" /><line x1="4" y1="20" x2="12" y2="20" />
    <path d="M15 8 L19 8 M15 18 L19 18" /><path d="M19 8 v10" />
  </>,
  // content analysis: counts as bars
  content_analysis: <>
    <line x1="4" y1="19" x2="20" y2="19" />
    <line x1="7" y1="16" x2="7" y2="8" /><line x1="12" y1="16" x2="12" y2="5" /><line x1="17" y1="16" x2="17" y2="11" />
  </>,
  // framework: the matrix
  framework: <>
    <rect x="4" y="4" width="16" height="16" rx="1.5" />
    <line x1="12" y1="4" x2="12" y2="20" /><line x1="4" y1="12" x2="20" y2="12" />
  </>,
  // literature synthesis: papers, one reading across them
  literature_synthesis: <>
    <rect x="4" y="7" width="11" height="13" rx="1.5" /><path d="M8 4 h11 v13" />
    <line x1="7" y1="12" x2="12" y2="12" /><line x1="7" y1="15.5" x2="12" y2="15.5" />
  </>,
}

export default function MethodGlyph({ method, size = 20, className = '' }:
  { method: string; size?: number; className?: string }) {
  const body = PATHS[method]
  if (!body) return null
  return (
    <svg className={`glyph ${className}`} width={size} height={size} viewBox="0 0 24 24"
      aria-hidden="true" {...STROKE}>{body}</svg>
  )
}
