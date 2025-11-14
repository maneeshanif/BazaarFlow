"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mail, MessageSquare, Send, CheckCircle2, Phone, MapPin } from "lucide-react";

export default function ContactPage() {
  const [sent, setSent] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    message: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSent(true);
    setTimeout(() => {
      setFormData({ name: "", email: "", phone: "", message: "" });
    }, 2000);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  return (
  <div className="min-h-screen py-20 px-4 bg-gradient-to-br from-[rgb(var(--muted))] via-white to-[rgb(var(--muted))]">
      <div className="container mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Header */}
          <div className="text-center mb-12">
            <Badge className="mb-4 px-4 py-1.5 bg-[#427A76] text-white border-[#427A76]">
              <MessageSquare className="w-3 h-3 mr-1" />
              Get in Touch
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 text-[#174143]">Contact Us</h1>
            <p className="text-lg text-[#427A76] max-w-2xl mx-auto">
              Have questions? We&rsquo;d love to hear from you. Send us a message or reach out via WhatsApp.
            </p>
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Contact Form */}
            <div className="lg:col-span-2">
              <Card className="border-2 shadow-xl bg-white backdrop-blur-sm border-[#427A76]/20">
                <CardHeader className="bg-white border-b border-[#427A76]/20">
                  <CardTitle className="flex items-center gap-2 text-[#174143]">
                    <Mail className="w-5 h-5" />
                    Send us a Message
                  </CardTitle>
                  <CardDescription className="text-[#427A76]">
                    Fill out the form below and we&rsquo;ll get back to you as soon as possible
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">Your Name *</Label>
                        <Input
                          id="name"
                          name="name"
                          value={formData.name}
                          onChange={handleChange}
                          placeholder="Enter your name"
                          required
                          className="border-primary/20 focus:border-primary"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="email">Email Address *</Label>
                        <Input
                          id="email"
                          name="email"
                          type="email"
                          value={formData.email}
                          onChange={handleChange}
                          placeholder="your@email.com"
                          required
                          className="border-primary/20 focus:border-primary"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone">Phone Number (Optional)</Label>
                      <Input
                        id="phone"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        placeholder="+92 300 1234567"
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="message">Your Message *</Label>
                      <Textarea
                        id="message"
                        name="message"
                        value={formData.message}
                        onChange={handleChange}
                        placeholder="Tell us how we can help you..."
                        rows={6}
                        required
                        className="border-primary/20 focus:border-primary resize-none"
                      />
                    </div>

                    {sent && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-green-700 dark:text-green-400 flex items-center gap-3"
                      >
                        <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                        <p className="text-sm font-medium">
                          Thanks! We&rsquo;ve received your message and will respond via email or WhatsApp soon.
                        </p>
                      </motion.div>
                    )}

                    <Button
                      type="submit"
                      size="lg"
                      className="w-full bg-[#174143] text-white hover:bg-[#427A76]"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Send Message
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </div>

            {/* Contact Info */}
            <div className="space-y-6">
              <Card className="border-2 bg-white border-[#427A76]/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#174143]">
                    <Phone className="w-5 h-5" />
                    Contact Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-muted-foreground">Email</h4>
                    <a
                      href="mailto:hello@bazaarflow.example"
                      className="text-primary hover:underline flex items-center gap-2"
                    >
                      <Mail className="w-4 h-4" />
                      hello@bazaarflow.example
                    </a>
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-muted-foreground">WhatsApp</h4>
                    <a
                      href="https://wa.me/923001234567"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-2"
                    >
                      <MessageSquare className="w-4 h-4" />
                      +92 300 1234567
                    </a>
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-muted-foreground">Location</h4>
                    <p className="flex items-start gap-2 text-sm">
                      <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      Karachi, Pakistan
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-2 bg-white border-[#427A76]/20">
                <CardHeader>
                  <CardTitle className="text-[#174143]">Business Hours</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Monday - Friday</span>
                    <span className="font-semibold">9:00 AM - 6:00 PM</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Saturday</span>
                    <span className="font-semibold">10:00 AM - 4:00 PM</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Sunday</span>
                    <span className="font-semibold">Closed</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
