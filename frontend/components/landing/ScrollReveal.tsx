"use client";

import {
  type ComponentPropsWithoutRef,
  type CSSProperties,
  type ElementType,
  type Ref,
  useEffect,
  useRef,
  useState,
} from "react";

import { cn } from "@/lib/utils";

type RevealDirection = "up" | "down";

type ScrollRevealProps<T extends ElementType> = {
  as?: T;
  children: React.ReactNode;
  className?: string;
  delayMs?: number;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mediaQuery.matches);

    update();
    mediaQuery.addEventListener("change", update);
    return () => mediaQuery.removeEventListener("change", update);
  }, []);

  return reducedMotion;
}

export default function ScrollReveal<T extends ElementType = "div">({
  as,
  children,
  className,
  delayMs = 0,
  ...props
}: ScrollRevealProps<T>) {
  const Component = as ?? "div";
  const ref = useRef<HTMLElement | null>(null);
  const reducedMotion = useReducedMotion();
  const [isVisible, setIsVisible] = useState(reducedMotion);
  const [direction, setDirection] = useState<RevealDirection>("down");

  useEffect(() => {
    if (reducedMotion) {
      setIsVisible(true);
      return;
    }

    if (typeof window === "undefined") return;

    let lastScrollY = window.scrollY;

    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      setDirection(currentScrollY > lastScrollY ? "down" : "up");
      lastScrollY = currentScrollY;
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [reducedMotion]);

  useEffect(() => {
    if (reducedMotion) return;
    if (typeof window === "undefined") return;
    if (typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return;
    }

    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      {
        threshold: 0.2,
        rootMargin: "-8% 0px -8% 0px",
      },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [reducedMotion]);

  const componentProps = {
    ...props,
    ref: ref as Ref<HTMLElement>,
    className: cn(
      "landing-reveal",
      isVisible ? "landing-reveal-visible" : "landing-reveal-hidden",
      direction === "down" ? "landing-reveal-from-bottom" : "landing-reveal-from-top",
      className,
    ),
    style: {
      transitionDelay: `${delayMs}ms`,
    } satisfies CSSProperties,
  } as ComponentPropsWithoutRef<T> & {
    ref: Ref<HTMLElement>;
    className: string;
    style: CSSProperties;
  };

  return (
    <Component
      {...componentProps}
    >
      {children}
    </Component>
  );
}
