import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header className="glass-header sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-white">Price Tracker</span>
          </Link>
          <nav className="flex gap-6">
            <Link to="/" className="text-white/60 hover:text-white font-medium transition-colors">
              Dashboard
            </Link>
            <Link to="/search" className="text-white/60 hover:text-white font-medium transition-colors">
              Search
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
