"use client";

import React from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { 
  BrainCircuit, 
  ArrowRight, 
  PlayCircle, 
  Sparkles, 
  TrendingUp, 
  Target, 
  Calendar,
  Code2
} from "lucide-react";

export default function NewLandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-white selection:bg-cyan-100 selection:text-cyan-900">
      {/* Subtle Background Glows */}
      <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-cyan-100/50 blur-3xl" />
      <div className="absolute -right-24 bottom-0 h-96 w-96 rounded-full bg-indigo-50/50 blur-3xl" />

      {/* Header / Logo Section */}
      <header className="relative z-10 mx-auto max-w-7xl px-6 py-8 md:px-12">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-200/50">
            <BrainCircuit className="h-7 w-7 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              AI Learning Hub
            </h2>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
              Structured AI learning
            </p>
          </div>
        </div>
      </header>

      {/* Hero Content */}
      <main className="relative z-10 mx-auto grid max-w-7xl px-6 pt-4 md:px-12 lg:grid-cols-2 lg:items-center lg:pt-12">
        
        {/* Left Side: Illustration */}
        <div className="relative order-2 mt-12 lg:order-1 lg:mt-0">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative"
          >
            {/* The Main Illustration Container */}
            <div className="relative aspect-square w-full max-w-[600px] flex items-center justify-center">
              {/* Main Hero Illustration from Generated Image */}
              <motion.div
                initial={{ opacity: 0, scale: 0.9, rotate: -2 }}
                animate={{ opacity: 1, scale: 1, rotate: 0 }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                className="relative z-0 h-full w-full overflow-hidden rounded-[3rem] shadow-2xl shadow-cyan-100"
              >
                <img 
                  src="/images/landing-hero.png" 
                  alt="AI Learning Path Illustration" 
                  className="h-full w-full object-cover opacity-90 transition-transform duration-10000 hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-tr from-white/40 via-transparent to-transparent" />
              </motion.div>

              {/* Floating Badges / UI Elements on top of the image */}
              <FloatingBadge 
                icon={<TrendingUp className="h-4 w-4" />} 
                label="Skill" 
                className="top-[15%] left-[-5%] z-10" 
                delay={0.6}
              />
              <FloatingBadge 
                icon={<Sparkles className="h-4 w-4" />} 
                label="Current Level" 
                className="bottom-[25%] left-[5%] z-10" 
                delay={0.8}
              />
              <FloatingBadge 
                icon={<Target className="h-4 w-4" />} 
                label="Goal Achieved" 
                className="top-[30%] right-[-5%] z-10 bg-orange-50 text-orange-600 border-orange-100" 
                delay={1.0}
              />
            </div>

            {/* Background Image Fade (to give it that 'AI' feel from the reference) */}
            <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_center,_transparent_0%,_white_70%)]" />
          </motion.div>
        </div>

        {/* Right Side: Text & Actions */}
        <div className="order-1 lg:order-2 lg:pl-12">
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="space-y-8"
          >
            <div className="space-y-4">
              <h1 className="text-5xl font-extrabold leading-[1.1] tracking-tight text-slate-900 md:text-6xl lg:text-7xl">
                Your Personal <br />
                <span className="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                  Path to Mastery
                </span>
              </h1>
              <p className="max-w-md text-lg leading-relaxed text-slate-500 md:text-xl">
                Adaptive, tailored learning modules created just for your goals.
              </p>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <Link
                href="/onboarding"
                className="group relative flex items-center justify-center gap-2 overflow-hidden rounded-full bg-blue-600 px-8 py-4 text-lg font-semibold text-white transition-all hover:bg-blue-700 hover:shadow-xl hover:shadow-blue-200 active:scale-[0.98]"
              >
                <span>Get Your Own Learning Path</span>
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-500 group-hover:translate-x-full" />
              </Link>
              
              <Link
                href="/how-it-works"
                className="flex items-center justify-center gap-2 rounded-full border-2 border-slate-200 bg-white px-8 py-4 text-lg font-semibold text-slate-700 transition-all hover:border-slate-300 hover:bg-slate-50 active:scale-[0.98]"
              >
                <PlayCircle className="h-5 w-5" />
                <span>See How It Works</span>
              </Link>
            </div>
            
            {/* Subtle Social Proof or Detail */}
            <div className="flex items-center gap-4 pt-4 text-sm font-medium text-slate-400">
              <div className="flex -space-x-2">
                {[1,2,3].map(i => (
                  <div key={i} className="h-8 w-8 rounded-full border-2 border-white bg-slate-100" />
                ))}
              </div>
              <p>Joined by 500+ AI enthusiasts this week</p>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Decorative background circle */}
      <div className="absolute -right-64 -top-64 h-[600px] w-[600px] rounded-full border border-slate-100 p-20 opacity-50">
        <div className="h-full w-full rounded-full border border-slate-50" />
      </div>
    </div>
  );
}

function FloatingBadge({ icon, label, className, delay = 0 }: { icon: React.ReactNode, label: string, className?: string, delay?: number }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      className={`absolute flex items-center gap-2 rounded-2xl border border-white bg-white/80 p-3 shadow-lg backdrop-blur-md ${className}`}
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
        {icon}
      </div>
      <span className="pr-2 text-sm font-bold text-slate-700">{label}</span>
    </motion.div>
  );
}

function FloatingIcon({ icon, className, delay = 0 }: { icon: React.ReactNode, className?: string, delay?: number }) {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ 
        delay, 
        duration: 0.5,
        scale: {
          type: "spring",
          damping: 12,
          stiffness: 100
        }
      }}
      className={`absolute flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-100 bg-white text-slate-400 shadow-sm ${className}`}
    >
      {icon}
    </motion.div>
  );
}
