"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

// Register GSAP plugins
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

interface CardData {
  icon: LucideIcon;
  title: string;
  desc: string;
  color: string;
  bg: string;
  border: string;
}

interface MeridianCardsProps {
  cards: CardData[];
  columns?: number;
}

export function MeridianCards({ cards, columns = 3 }: MeridianCardsProps) {
  const cardsRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (!cardsRef.current) return;

    const ctx = gsap.context(() => {
      // Set initial state - all cards at center point
      cardRefs.current.forEach((card) => {
        if (card) {
          gsap.set(card, {
            opacity: 0,
            scale: 0.3,
            x: 0,
            y: 0,
          });
        }
      });

      // Animate cards expanding from center
      ScrollTrigger.create({
        trigger: cardsRef.current,
        start: "top 80%",
        onEnter: () => {
          cardRefs.current.forEach((card, index) => {
            if (card) {
              gsap.to(card, {
                opacity: 1,
                scale: 1,
                x: 0,
                y: 0,
                duration: 0.8,
                delay: index * 0.1,
                ease: "power3.out",
              });
            }
          });
        },
      });
    }, cardsRef);

    return () => ctx.revert();
  }, []);

  const gridClass = columns === 2 ? "md:grid-cols-2" : columns === 4 ? "md:grid-cols-4" : "md:grid-cols-3";

  return (
    <div ref={cardsRef} className={`grid ${gridClass} gap-6`}>
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <div
            key={i}
            ref={(el) => {
              cardRefs.current[i] = el;
            }}
            className="card-item"
          >
            <Card
              className={`h-full border-2 ${card.border} bg-white hover:shadow-lg transition-all rounded-2xl cursor-pointer group`}
              style={{ transformOrigin: "center center" }}
            >
              <CardHeader className="pb-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center mb-4 shadow-sm group-hover:scale-110 transition-transform`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <CardTitle className="text-lg font-semibold text-slate-900">{card.title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-sm text-slate-600 leading-relaxed">{card.desc}</p>
              </CardContent>
            </Card>
          </div>
        );
      })}
    </div>
  );
}

