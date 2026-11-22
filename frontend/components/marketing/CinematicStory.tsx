"use client";

import Link from "next/link";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useScroll,
  useSpring,
  type MotionValue,
} from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";


type Chapter = {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  videoUrl: string;
  href: string;
  cta: string;
  accent: string;
  poster: string;
};

const CHAPTERS: Chapter[] = [
  {
    id: "01",
    title: "Sepsis Intelligence",
    subtitle: "Six-hour onset odds, with named drivers.",
    description:
      "Live ICU vitals into a frozen LightGBM sepsis score. TrustGate holds bad feeds. The clinician keeps the call.",
    videoUrl: "/videos/auralis-clinical-intelligence.mp4",
    href: "/product",
    cta: "See the platform",
    accent: "#73C3CF",
    poster: "linear-gradient(135deg, #0B1422 0%, #142538 42%, #1F6370 100%)",
  },
  {
    id: "02",
    title: "Hospital Integration",
    subtitle: "Devices, labs, EHR — one validated path.",
    description:
      "HL7 and FHIR in. TrustGate checks freshness and shape before anything touches the model.",
    videoUrl: "/videos/auralis-hospital-integration.mp4",
    href: "/deployment-integration",
    cta: "HL7 and FHIR path",
    accent: "#4FA8B7",
    poster: "linear-gradient(145deg, #0B1422 0%, #123047 48%, #287A88 100%)",
  },
  {
    id: "03",
    title: "Beyond Deployment",
    subtitle: "Engineers on the ward after go-live.",
    description:
      "Readiness, feed validation, staff enablement — then the support that stays when the pilot ends.",
    videoUrl: "/videos/auralis-beyond-deployment.mp4",
    href: "/forward-deployed-engineering",
    cta: "Forward deployed engineering",
    accent: "#A8D9BE",
    poster: "linear-gradient(160deg, #0B1422 0%, #16324A 55%, #1F7A4D 100%)",
  },
];

const textContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

const textReveal = {
  hidden: { y: "110%", opacity: 0 },
  visible: {
    y: "0%",
    opacity: 1,
    transition: { duration: 0.75, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const fadeIn = {
  hidden: { opacity: 0, y: 18 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay: 0.18, ease: [0.22, 1, 0.36, 1] as const },
  },
};

function FilmGrain() {
  return (
    <div className="pointer-events-none absolute inset-0 z-20 opacity-[0.05] mix-blend-overlay" aria-hidden>
      <div
        className="absolute inset-0 h-full w-full"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
}

function VideoLayer({
  chapter,
  active,
  warm,
  allowLoad,
  reduceMotion,
}: {
  chapter: Chapter;
  active: boolean;
  /** Prefetch next/prev chapter only — never all three at once. */
  warm: boolean;
  /** Section near viewport — keeps hero/first paint free of video bytes. */
  allowLoad: boolean;
  reduceMotion: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  const shouldMount = allowLoad && (active || warm) && !reduceMotion && !failed;

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !shouldMount) return;

    if (!active) {
      el.pause();
      return;
    }

    // Autoplay can throw AbortError when the chapter flips mid-play — never treat that as a hard fail.
    const tryPlay = () => {
      el.muted = true;
      const run = el.play();
      if (run && typeof run.then === "function") {
        void run.catch((err: unknown) => {
          const name = err instanceof Error ? err.name : "";
          if (name !== "AbortError" && name !== "NotAllowedError") {
            setFailed(true);
          }
        });
      }
    };

    if (el.readyState >= 2) tryPlay();
    else {
      const onCanPlay = () => tryPlay();
      el.addEventListener("canplay", onCanPlay, { once: true });
      el.load();
      return () => el.removeEventListener("canplay", onCanPlay);
    }
  }, [active, shouldMount, chapter.videoUrl]);

  return (
    <motion.div
      className="absolute inset-0 h-full w-full"
      initial={false}
      animate={{ opacity: active ? 1 : 0 }}
      transition={{ duration: reduceMotion ? 0 : 0.9, ease: "easeInOut" }}
      style={{ zIndex: active ? 10 : 0, visibility: active ? "visible" : "hidden" }}
      aria-hidden={!active}
    >
      <div className="absolute inset-0" style={{ background: chapter.poster }} />
      {shouldMount && (
        <video
          ref={videoRef}
          src={chapter.videoUrl}
          className="absolute inset-0 h-full w-full object-cover opacity-100"
          muted
          loop
          playsInline
          autoPlay={active}
          preload={active ? "auto" : "metadata"}
          onError={() => setFailed(true)}
        />
      )}
      {/* Soft vignette — lighter so footage stays readable */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-[#0B1422]/55 via-[#0B1422]/20 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0B1422]/45 via-transparent to-[#0B1422]/15" />
      {active && failed && (
        <div className="absolute inset-0 flex items-end p-8 sm:p-12">
          <p className="max-w-sm text-xs uppercase tracking-[0.2em] text-white/45">
            Chapter still · {chapter.title}
          </p>
        </div>
      )}
    </motion.div>
  );
}

function ChapterDock({
  activeIndex,
  progress,
  visible,
}: {
  activeIndex: number;
  progress: MotionValue<number>;
  visible: boolean;
}) {
  const smooth = useSpring(progress, { stiffness: 120, damping: 28, mass: 0.4 });
  const chapter = CHAPTERS[activeIndex];

  return (
    <AnimatePresence>
      {visible ? (
        <motion.div
          className="pointer-events-none fixed bottom-6 left-1/2 z-40 -translate-x-1/2 sm:bottom-8"
          initial={{ y: 28, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 20, opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="pointer-events-auto flex items-center gap-3 rounded-full border border-white/10 bg-[#0B1422]/88 py-1.5 pl-5 pr-1.5 shadow-lift backdrop-blur-xl sm:gap-4 sm:pr-2">
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-[0.18em] text-white/45">Chapter {chapter.id}</p>
              <AnimatePresence mode="wait">
                <motion.p
                  key={chapter.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="truncate text-xs font-semibold text-white"
                >
                  {chapter.title}
                </motion.p>
              </AnimatePresence>
            </div>
            <div className="relative flex h-11 w-11 items-center justify-center">
              <svg className="h-full w-full -rotate-90" viewBox="0 0 48 48" aria-hidden>
                <circle cx="24" cy="24" r="18" className="stroke-white/15" strokeWidth="2" fill="none" />
                <motion.circle
                  cx="24"
                  cy="24"
                  r="18"
                  className="stroke-[#73C3CF]"
                  strokeWidth="2"
                  fill="none"
                  strokeLinecap="round"
                  style={{ pathLength: smooth }}
                />
              </svg>
              <Icon name="activity" size={14} className="absolute text-white" />
            </div>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

function StaticFallback() {
  return (
    <section className="border-b border-[#C9E6D6]/70 bg-navy text-white">
      <div className="auralis-container-public grid gap-6 py-16 sm:py-20 lg:grid-cols-3 lg:gap-8 lg:py-24">
        {CHAPTERS.map((chapter) => (
          <article key={chapter.id} className="border-t border-white/15 pt-6">
            <p className="font-mono text-[11px] tracking-[0.2em] text-[#73C3CF]">{chapter.id}</p>
            <h3 className="mt-3 font-display text-[1.65rem] font-semibold leading-[1.05] tracking-[-0.03em]">
              {chapter.title}
            </h3>
            <p className="mt-3 font-sans text-[15px] font-medium leading-snug text-white/80">{chapter.subtitle}</p>
            <p className="mt-2 text-sm leading-6 text-white/55">{chapter.description}</p>
            <Link href={chapter.href} className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-[#73C3CF]">
              {chapter.cta}
              <Icon name="arrow-right" size={14} />
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

/** Scroll-driven three-chapter cinematic story for the public homepage. */
export function CinematicStory() {
  const reduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [inView, setInView] = useState(false);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting && entry.intersectionRatio > 0.05),
      { threshold: [0, 0.05, 0.2, 0.5] },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (reduceMotion) return;
    return scrollYProgress.on("change", (latest) => {
      const next = Math.min(Math.floor(latest * CHAPTERS.length), CHAPTERS.length - 1);
      setActiveIndex(Number.isFinite(next) ? Math.max(0, next) : 0);
    });
  }, [reduceMotion, scrollYProgress]);

  if (reduceMotion) return <StaticFallback />;

  return (
    <section
      ref={containerRef}
      className="relative w-full bg-navy"
      style={{ height: `${CHAPTERS.length * 100}vh` }}
      aria-label="Auralis story chapters"
    >
      <div className="sticky top-0 h-[100svh] w-full overflow-hidden">
        <div className="absolute inset-0">
          {CHAPTERS.map((chapter, index) => (
            <VideoLayer
              key={chapter.id}
              chapter={chapter}
              active={index === activeIndex}
              warm={Math.abs(index - activeIndex) === 1}
              allowLoad={inView}
              reduceMotion={Boolean(reduceMotion)}
            />
          ))}
          <FilmGrain />
        </div>

        <div className="relative z-30 flex h-full items-center px-5 sm:px-10 lg:px-20">
          <div className="auralis-container-public w-full !px-0">
            <AnimatePresence mode="wait">
              <motion.div
                key={CHAPTERS[activeIndex].id}
                variants={textContainer}
                initial="hidden"
                animate="visible"
                exit="hidden"
                className="max-w-2xl"
              >
                <motion.div variants={fadeIn} className="mb-4 flex items-baseline gap-3">
                  <span
                    className="font-mono text-sm font-medium tracking-[0.28em] text-[#73C3CF] sm:text-base"
                    style={{ color: CHAPTERS[activeIndex].accent }}
                  >
                    {CHAPTERS[activeIndex].id}
                  </span>
                  <span className="h-px flex-1 max-w-[4.5rem] bg-white/25" aria-hidden />
                  <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/40">
                    Chapter
                  </span>
                </motion.div>

                <div className="mb-4 overflow-hidden py-0.5">
                  <motion.h2
                    variants={textReveal}
                    className="font-display text-[2.35rem] font-semibold leading-[0.98] tracking-[-0.04em] text-white sm:text-[3.75rem] lg:text-[4.25rem]"
                  >
                    {CHAPTERS[activeIndex].title}
                  </motion.h2>
                </div>

                <motion.p
                  variants={fadeIn}
                  className="max-w-md font-sans text-[15px] font-medium leading-snug tracking-[-0.01em] text-white/85 sm:text-[17px]"
                >
                  {CHAPTERS[activeIndex].subtitle}
                </motion.p>

                <motion.p
                  variants={fadeIn}
                  className="mt-3 max-w-sm font-sans text-[13px] leading-6 text-white/55 sm:text-sm sm:leading-6"
                >
                  {CHAPTERS[activeIndex].description}
                </motion.p>

                <motion.div variants={fadeIn}>
                  <Link
                    href={CHAPTERS[activeIndex].href}
                    className="group mt-8 inline-flex items-center gap-3 text-sm font-semibold text-white"
                  >
                    <span className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-white/25">
                      <span className="absolute inset-0 translate-y-full bg-white transition-transform duration-300 group-hover:translate-y-0" />
                      <Icon
                        name="arrow-right"
                        size={15}
                        className="relative z-10 transition-colors duration-300 group-hover:text-navy"
                      />
                    </span>
                    <span className="text-xs tracking-[0.16em] uppercase">{CHAPTERS[activeIndex].cta}</span>
                  </Link>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Invisible scroll panes so sticky releases after the last chapter */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        {CHAPTERS.map((chapter) => (
          <div key={chapter.id} className="h-screen w-full" />
        ))}
      </div>

      <ChapterDock activeIndex={activeIndex} progress={scrollYProgress} visible={inView} />
    </section>
  );
}
