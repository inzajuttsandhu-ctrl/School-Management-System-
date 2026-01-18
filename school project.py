import json
import os
import datetime
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
from abc import ABC, abstractmethod


# ============================================
# 🎯 CONFIGURATION & SETUP
# ============================================
class AttendanceStatus(Enum):
    """Enum for attendance status"""
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"
    HOLIDAY = "Holiday"


class PaymentMethod(Enum):
    """Enum for payment methods"""
    CASH = "Cash"
    CARD = "Card"
    ONLINE = "Online"
    CHEQUE = "Cheque"


@dataclass
class Config:
    """Configuration for the system"""
    DATA_FILE: str = "school_data.pkl"
    LOG_FILE: str = "school_system.log"
    BACKUP_DIR: str = "backups"
    DEFAULT_STUDENT_FEES: float = 50000.0
    DATE_FORMAT: str = "%Y-%m-%d"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# ============================================
# 🎯 LOGGING SETUP (Professional Practice)
# ============================================
def setup_logging(log_file: str = "school_system.log") -> logging.Logger:
    """Setup professional logging"""
    logger = logging.getLogger(__name__)
    
    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()
    
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logging()


# ============================================
# 🎯 ABSTRACT BASE CLASSES
# ============================================
class Serializable(ABC):
    """Interface for serializable objects"""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary"""
        pass
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load object from dictionary"""
        pass


class Person(Serializable):
    """Base class for all persons in the system"""
    
    def __init__(self, person_id: str, name: str, age: int, email: str = ""):
        """
        Initialize a person
        
        Args:
            person_id: Unique identifier
            name: Full name
            age: Age in years
            email: Email address
        """
        if not person_id or not name:
            raise ValueError("person_id and name are required")
        if age <= 0 or age > 150:
            raise ValueError(f"Invalid age: {age}")
        
        self.person_id = person_id
        self.name = name
        self.age = age
        self.email = email
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
        
        logger.info(f"Person created: {name} (ID: {person_id})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert person to dictionary"""
        return {
            'person_id': self.person_id,
            'name': self.name,
            'age': self.age,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load person from dictionary"""
        if not data:
            raise ValueError("Empty data dictionary")
        
        self.person_id = data.get('person_id', '')
        self.name = data.get('name', '')
        self.age = data.get('age', 0)
        self.email = data.get('email', '')
        
        # Handle datetime conversion safely
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')
        
        if created_at:
            self.created_at = datetime.datetime.fromisoformat(created_at)
        else:
            self.created_at = datetime.datetime.now()
            
        if updated_at:
            self.updated_at = datetime.datetime.fromisoformat(updated_at)
        else:
            self.updated_at = datetime.datetime.now()
    
    def update(self, **kwargs):
        """Update person details"""
        if not kwargs:
            return
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                # Validate specific fields
                if key == 'age' and (value <= 0 or value > 150):
                    raise ValueError(f"Invalid age: {value}")
                if key == 'email' and value:
                    # Simple email validation
                    if '@' not in value:
                        raise ValueError(f"Invalid email format: {value}")
                
                setattr(self, key, value)
            else:
                logger.warning(f"Ignoring unknown attribute: {key}")
        
        self.updated_at = datetime.datetime.now()
        logger.debug(f"Person updated: {self.name}")
    
    def __str__(self) -> str:
        return f"{self.name} (ID: {self.person_id})"
    
    def __repr__(self) -> str:
        return f"Person(name='{self.name}', id='{self.person_id}')"


# ============================================
# 🎯 STUDENT CLASS (FIXED)
# ============================================
@dataclass
class FeesRecord:
    """Data class for fees records"""
    amount: float
    date: datetime.datetime
    method: PaymentMethod
    description: str = ""
    receipt_no: str = ""


class Student(Person):
    """Student class with attendance and fees tracking"""
    
    def __init__(self, student_id: str, name: str, age: int, 
                 student_class: str, roll_no: int, email: str = "", 
                 guardian_name: str = "", guardian_phone: str = ""):
        """
        Initialize a student
        
        Args:
            student_id: Unique student ID
            name: Student name
            age: Student age
            student_class: Class/grade
            roll_no: Roll number
            email: Email address (optional)
            guardian_name: Guardian's name (optional)
            guardian_phone: Guardian's phone (optional)
        """
        # Call parent class constructor with only Person parameters
        super().__init__(student_id, name, age, email)
        
        if not student_class:
            raise ValueError("student_class is required")
        if roll_no <= 0:
            raise ValueError(f"Invalid roll number: {roll_no}")
        
        self.student_class = student_class
        self.roll_no = roll_no
        self.subjects: List[str] = []
        self.attendance: Dict[str, str] = {}
        self.fees_paid: float = 0.0
        self.fees_due: float = Config.DEFAULT_STUDENT_FEES
        self.fees_records: List[FeesRecord] = []
        self.guardian_name: str = guardian_name
        self.guardian_phone: str = guardian_phone
        
        logger.info(f"Student created: {name}, Class: {student_class}")
    
    def mark_attendance(self, status: AttendanceStatus = AttendanceStatus.PRESENT,
                       date: Optional[datetime.date] = None) -> bool:
        """
        Mark attendance for a student
        
        Args:
            status: Attendance status
            date: Date for attendance (defaults to today)
        
        Returns:
            bool: Success status
        """
        if date is None:
            date = datetime.date.today()
        
        # Check if date is in future
        if date > datetime.date.today():
            logger.warning(f"Cannot mark attendance for future date: {date}")
            return False
        
        date_str = date.strftime(Config.DATE_FORMAT)
        
        # Check if attendance already marked
        if date_str in self.attendance:
            logger.warning(f"Attendance already marked for {date_str}")
            return False
        
        self.attendance[date_str] = status.value
        
        logger.info(f"Attendance marked: {self.name} - {status.value} on {date_str}")
        return True
    
    def get_attendance_percentage(self, month: Optional[int] = None,
                                 year: Optional[int] = None) -> float:
        """
        Calculate attendance percentage
        
        Args:
            month: Optional month filter (1-12)
            year: Optional year filter
        
        Returns:
            float: Attendance percentage (0-100)
        """
        if not self.attendance:
            return 0.0
        
        # Validate month input
        if month is not None and (month < 1 or month > 12):
            raise ValueError(f"Invalid month: {month}. Must be 1-12")
        
        filtered_attendance = self.attendance
        
        if month or year:
            filtered_attendance = {}
            for date_str, status in self.attendance.items():
                try:
                    date = datetime.datetime.strptime(date_str, Config.DATE_FORMAT).date()
                    if (month is None or date.month == month) and \
                       (year is None or date.year == year):
                        filtered_attendance[date_str] = status
                except ValueError as e:
                    logger.error(f"Invalid date format in attendance record: {date_str} - {e}")
                    continue
        
        if not filtered_attendance:
            return 0.0
        
        present_days = sum(1 for status in filtered_attendance.values()
                          if status == AttendanceStatus.PRESENT.value)
        total_days = len(filtered_attendance)
        
        if total_days == 0:
            return 0.0
        
        return (present_days / total_days) * 100
    
    def pay_fees(self, amount: float, method: PaymentMethod,
                description: str = "") -> bool:
        """
        Process fee payment
        
        Args:
            amount: Payment amount
            method: Payment method
            description: Payment description
        
        Returns:
            bool: Success status
        """
        try:
            # Validation
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if amount > self.fees_due:
                raise ValueError(f"Amount exceeds due amount: {self.fees_due}")
            
            # Process payment
            self.fees_paid += amount
            self.fees_due -= amount
            
            # Record transaction
            receipt = FeesRecord(
                amount=amount,
                date=datetime.datetime.now(),
                method=method,
                description=description,
                receipt_no=f"REC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            self.fees_records.append(receipt)
            
            logger.info(f"Fees paid: {self.name} - ₹{amount} via {method.value}")
            return True
            
        except ValueError as e:
            logger.error(f"Fee payment failed for {self.name}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error in fee payment: {e}")
            return False
    
    def get_fees_summary(self) -> Dict[str, Any]:
        """Get comprehensive fees summary"""
        try:
            payment_percentage = (self.fees_paid / Config.DEFAULT_STUDENT_FEES) * 100 if Config.DEFAULT_STUDENT_FEES > 0 else 0
            last_payment = self.fees_records[-1].date if self.fees_records else None
        except ZeroDivisionError:
            payment_percentage = 0
            logger.error("DEFAULT_STUDENT_FEES is set to 0")
        
        return {
            'student_name': self.name,
            'student_id': self.person_id,
            'total_fees': Config.DEFAULT_STUDENT_FEES,
            'fees_paid': self.fees_paid,
            'fees_due': max(self.fees_due, 0),  # Ensure non-negative
            'payment_percentage': min(payment_percentage, 100),  # Cap at 100%
            'total_transactions': len(self.fees_records),
            'last_payment': last_payment
        }
    
    def display_info(self, detailed: bool = False) -> str:
        """
        Display student information
        
        Args:
            detailed: Whether to show detailed information
        
        Returns:
            str: Formatted information
        """
        try:
            attendance_percentage = self.get_attendance_percentage()
            payment_progress = (self.fees_paid / Config.DEFAULT_STUDENT_FEES) * 100 if Config.DEFAULT_STUDENT_FEES > 0 else 0
        except Exception as e:
            attendance_percentage = 0
            payment_progress = 0
            logger.error(f"Error calculating display info: {e}")
        
        info = [
            f"\n{'='*50}",
            f"🎓 STUDENT INFORMATION",
            f"{'='*50}",
            f"ID: {self.person_id}",
            f"Name: {self.name}",
            f"Age: {self.age}",
            f"Class: {self.student_class}",
            f"Roll No: {self.roll_no}",
            f"Email: {self.email or 'Not provided'}",
            f"\n📊 ACADEMIC:",
            f"  Subjects: {', '.join(self.subjects) if self.subjects else 'None'}",
            f"  Attendance: {attendance_percentage:.1f}%",
            f"\n💰 FINANCIAL:",
            f"  Fees Paid: ₹{self.fees_paid:,.2f}",
            f"  Fees Due: ₹{self.fees_due:,.2f}",
            f"  Payment Progress: {payment_progress:.1f}%",
        ]
        
        if detailed and self.guardian_name:
            info.extend([
                f"\n👨‍👩‍👧‍👦 GUARDIAN:",
                f"  Name: {self.guardian_name}",
                f"  Phone: {self.guardian_phone or 'Not provided'}"
            ])
        
        info.append(f"{'='*50}")
        return "\n".join(info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert student to dictionary"""
        data = super().to_dict()
        data.update({
            'type': 'student',
            'student_class': self.student_class,
            'roll_no': self.roll_no,
            'subjects': self.subjects,
            'attendance': self.attendance,
            'fees_paid': self.fees_paid,
            'fees_due': self.fees_due,
            'fees_records': [
                {
                    'amount': record.amount,
                    'date': record.date.isoformat(),
                    'method': record.method.value,
                    'description': record.description,
                    'receipt_no': record.receipt_no
                }
                for record in self.fees_records
            ],
            'guardian_name': self.guardian_name,
            'guardian_phone': self.guardian_phone
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load student from dictionary"""
        try:
            super().from_dict(data)
            self.student_class = data.get('student_class', '')
            self.roll_no = data.get('roll_no', 0)
            self.subjects = data.get('subjects', [])
            self.attendance = data.get('attendance', {})
            self.fees_paid = float(data.get('fees_paid', 0.0))
            self.fees_due = float(data.get('fees_due', Config.DEFAULT_STUDENT_FEES))
            
            self.fees_records = []
            for record_data in data.get('fees_records', []):
                try:
                    record = FeesRecord(
                        amount=float(record_data.get('amount', 0)),
                        date=datetime.datetime.fromisoformat(record_data['date']),
                        method=PaymentMethod(record_data['method']),
                        description=record_data.get('description', ''),
                        receipt_no=record_data.get('receipt_no', '')
                    )
                    self.fees_records.append(record)
                except (KeyError, ValueError) as e:
                    logger.error(f"Error loading fee record: {e}")
                    continue
            
            self.guardian_name = data.get('guardian_name', '')
            self.guardian_phone = data.get('guardian_phone', '')
            
        except Exception as e:
            logger.error(f"Error loading student data: {e}")
            raise


# ============================================
# 🎯 TEACHER CLASS (FIXED)
# ============================================
class Teacher(Person):
    """Teacher class with salary and subject management"""
    
    def __init__(self, teacher_id: str, name: str, age: int, 
                 subject: str, salary: float, email: str = ""):
        """
        Initialize a teacher
        
        Args:
            teacher_id: Unique teacher ID
            name: Teacher name
            age: Teacher age
            subject: Teaching subject
            salary: Monthly salary
            email: Email address (optional)
        """
        super().__init__(teacher_id, name, age, email)
        
        if not subject:
            raise ValueError("subject is required")
        if salary <= 0:
            raise ValueError(f"Invalid salary: {salary}")
        
        self.subject = subject
        self.salary = salary
        self.qualification: str = ""
        self.experience_years: int = 0
        self.classes_taught: List[str] = []
        self.attendance: Dict[str, str] = {}
        self.salary_payments: List[Dict] = []
        
        logger.info(f"Teacher created: {name}, Subject: {subject}")
    
    def mark_attendance(self, status: AttendanceStatus = AttendanceStatus.PRESENT,
                       date: Optional[datetime.date] = None) -> bool:
        """
        Mark teacher attendance
        
        Args:
            status: Attendance status
            date: Date for attendance
        
        Returns:
            bool: Success status
        """
        if date is None:
            date = datetime.date.today()
        
        # Check if date is in future
        if date > datetime.date.today():
            logger.warning(f"Cannot mark attendance for future date: {date}")
            return False
        
        date_str = date.strftime(Config.DATE_FORMAT)
        
        # Check if attendance already marked
        if date_str in self.attendance:
            logger.warning(f"Attendance already marked for {date_str}")
            return False
        
        self.attendance[date_str] = status.value
        
        logger.debug(f"Teacher attendance: {self.name} - {status.value}")
        return True
    
    def receive_salary(self, bonus: float = 0.0, 
                      deductions: float = 0.0) -> bool:
        """
        Process salary payment
        
        Args:
            bonus: Additional bonus amount
            deductions: Salary deductions
        
        Returns:
            bool: Success status
        """
        try:
            if bonus < 0:
                raise ValueError("Bonus cannot be negative")
            if deductions < 0:
                raise ValueError("Deductions cannot be negative")
            
            net_salary = self.salary + bonus - deductions
            
            if net_salary <= 0:
                raise ValueError("Net salary must be positive")
            
            payment_record = {
                'date': datetime.datetime.now().isoformat(),
                'base_salary': self.salary,
                'bonus': bonus,
                'deductions': deductions,
                'net_salary': net_salary,
                'payment_id': f"SAL-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            self.salary_payments.append(payment_record)
            
            logger.info(f"Salary paid: {self.name} - ₹{net_salary:,.2f}")
            return True
            
        except ValueError as e:
            logger.error(f"Salary payment failed: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected salary error: {e}")
            return False
    
    def display_info(self, detailed: bool = False) -> str:
        """
        Display teacher information
        
        Args:
            detailed: Whether to show detailed information
        
        Returns:
            str: Formatted information
        """
        try:
            last_payment_info = ""
            if detailed and self.salary_payments:
                last_payment = self.salary_payments[-1]
                last_payment_info = f"\n  Last Payment: ₹{last_payment['net_salary']:,.2f} on {last_payment['date'][:10]}"
        except (KeyError, IndexError) as e:
            logger.error(f"Error getting last payment info: {e}")
            last_payment_info = ""
        
        info = [
            f"\n{'='*50}",
            f"👩‍🏫 TEACHER INFORMATION",
            f"{'='*50}",
            f"ID: {self.person_id}",
            f"Name: {self.name}",
            f"Age: {self.age}",
            f"Subject: {self.subject}",
            f"Salary: ₹{self.salary:,.2f}/month",
            f"Email: {self.email or 'Not provided'}",
            f"\n📚 PROFESSIONAL:",
            f"  Qualification: {self.qualification or 'Not specified'}",
            f"  Experience: {self.experience_years} years",
            f"  Classes: {', '.join(self.classes_taught) if self.classes_taught else 'None'}",
            f"  Salary Payments: {len(self.salary_payments)}",
        ]
        
        if detailed and last_payment_info:
            info.append(last_payment_info)
        
        info.append(f"{'='*50}")
        return "\n".join(info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert teacher to dictionary"""
        data = super().to_dict()
        data.update({
            'type': 'teacher',
            'subject': self.subject,
            'salary': self.salary,
            'qualification': self.qualification,
            'experience_years': self.experience_years,
            'classes_taught': self.classes_taught,
            'attendance': self.attendance,
            'salary_payments': self.salary_payments
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load teacher from dictionary"""
        try:
            super().from_dict(data)
            self.subject = data.get('subject', '')
            self.salary = float(data.get('salary', 0.0))
            self.qualification = data.get('qualification', '')
            self.experience_years = int(data.get('experience_years', 0))
            self.classes_taught = data.get('classes_taught', [])
            self.attendance = data.get('attendance', {})
            self.salary_payments = data.get('salary_payments', [])
        except Exception as e:
            logger.error(f"Error loading teacher data: {e}")
            raise


# ============================================
# 🎯 SCHOOL MANAGEMENT SYSTEM (FIXED)
# ============================================
class SchoolManagementSystem:
    """
    Main school management system
    
    Features:
    - Student & Teacher Management
    - Attendance Tracking
    - Financial Management
    - Data Persistence
    - Reporting
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the school management system
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.students: Dict[str, Student] = {}
        self.teachers: Dict[str, Teacher] = {}
        
        # Create backup directory
        os.makedirs(self.config.BACKUP_DIR, exist_ok=True)
        
        # Load existing data
        self.load_data()
        
        logger.info("School Management System initialized")
    
    def save_data(self, backup: bool = True) -> bool:
        """
        Save system data to file
        
        Args:
            backup: Whether to create a backup
        
        Returns:
            bool: Success status
        """
        try:
            # Create backup if requested
            if backup and os.path.exists(self.config.DATA_FILE):
                backup_file = os.path.join(
                    self.config.BACKUP_DIR,
                    f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
                )
                try:
                    with open(backup_file, 'wb') as f:
                        pickle.dump({
                            'students': {sid: student.to_dict() for sid, student in self.students.items()},
                            'teachers': {tid: teacher.to_dict() for tid, teacher in self.teachers.items()}
                        }, f)
                    logger.info(f"Backup created: {backup_file}")
                except Exception as e:
                    logger.error(f"Failed to create backup: {e}")
            
            # Save current data
            data = {
                'students': {sid: student.to_dict() for sid, student in self.students.items()},
                'teachers': {tid: teacher.to_dict() for tid, teacher in self.teachers.items()},
                'metadata': {
                    'last_saved': datetime.datetime.now().isoformat(),
                    'total_students': len(self.students),
                    'total_teachers': len(self.teachers),
                    'version': '1.0'
                }
            }
            
            # Use atomic write to prevent corruption
            temp_file = f"{self.config.DATA_FILE}.tmp"
            with open(temp_file, 'wb') as f:
                pickle.dump(data, f)
            
            # Rename temp file to actual file
            if os.path.exists(self.config.DATA_FILE):
                os.replace(temp_file, self.config.DATA_FILE)
            else:
                os.rename(temp_file, self.config.DATA_FILE)
            
            logger.info(f"Data saved to {self.config.DATA_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    def load_data(self) -> bool:
        """
        Load system data from file
        
        Returns:
            bool: Success status
        """
        try:
            if not os.path.exists(self.config.DATA_FILE):
                logger.warning("No data file found, starting fresh")
                return True  # Return True, not False, as empty system is valid
            
            with open(self.config.DATA_FILE, 'rb') as f:
                data = pickle.load(f)
            
            # Validate data structure
            if not isinstance(data, dict):
                logger.error("Invalid data format in file")
                return False
            
            # Load students
            self.students.clear()
            student_dict = data.get('students', {})
            if not isinstance(student_dict, dict):
                logger.error("Invalid students data format")
                return False
            
            for sid, student_data in student_dict.items():
                try:
                    student = Student("", "", 0, "", 0)
                    student.from_dict(student_data)
                    self.students[sid] = student
                except Exception as e:
                    logger.error(f"Error loading student {sid}: {e}")
                    continue
            
            # Load teachers
            self.teachers.clear()
            teacher_dict = data.get('teachers', {})
            if not isinstance(teacher_dict, dict):
                logger.error("Invalid teachers data format")
                return False
            
            for tid, teacher_data in teacher_dict.items():
                try:
                    teacher = Teacher("", "", 0, "", 0.0)
                    teacher.from_dict(teacher_data)
                    self.teachers[tid] = teacher
                except Exception as e:
                    logger.error(f"Error loading teacher {tid}: {e}")
                    continue
            
            logger.info(f"Data loaded: {len(self.students)} students, "
                       f"{len(self.teachers)} teachers")
            return True
            
        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"Corrupted data file: {e}")
            # Try to restore from backup
            return self.restore_from_backup()
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def restore_from_backup(self) -> bool:
        """Try to restore data from latest backup"""
        try:
            if not os.path.exists(self.config.BACKUP_DIR):
                return False
            
            # Find all backup files
            backup_files = []
            for file in os.listdir(self.config.BACKUP_DIR):
                if file.startswith("backup_") and file.endswith(".pkl"):
                    backup_files.append(file)
            
            if not backup_files:
                return False
            
            # Sort by date (newest first)
            backup_files.sort(reverse=True)
            
            # Try each backup from newest to oldest
            for backup_file in backup_files:
                backup_path = os.path.join(self.config.BACKUP_DIR, backup_file)
                try:
                    with open(backup_path, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Clear current data
                    self.students.clear()
                    self.teachers.clear()
                    
                    # Load from backup
                    for sid, student_data in data.get('students', {}).items():
                        student = Student("", "", 0, "", 0)
                        student.from_dict(student_data)
                        self.students[sid] = student
                    
                    for tid, teacher_data in data.get('teachers', {}).items():
                        teacher = Teacher("", "", 0, "", 0.0)
                        teacher.from_dict(teacher_data)
                        self.teachers[tid] = teacher
                    
                    logger.info(f"Restored from backup: {backup_file}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to restore from {backup_file}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    # ========== STUDENT MANAGEMENT ==========
    def add_student(self, student_id: str, name: str, age: int, 
                   student_class: str, roll_no: int, email: str = "", 
                   guardian_name: str = "", guardian_phone: str = "") -> Optional[Student]:
        """
        Add a new student
        
        Args:
            student_id: Student ID
            name: Student name
            age: Student age
            student_class: Student class
            roll_no: Roll number
            email: Email (optional)
            guardian_name: Guardian name (optional)
            guardian_phone: Guardian phone (optional)
        
        Returns:
            Optional[Student]: Created student or None
        """
        try:
            if student_id in self.students:
                raise ValueError(f"Student ID {student_id} already exists")
            
            # Validate roll number uniqueness in class
            for existing_student in self.students.values():
                if (existing_student.student_class == student_class and 
                    existing_student.roll_no == roll_no):
                    raise ValueError(f"Roll number {roll_no} already exists in class {student_class}")
            
            student = Student(
                student_id=student_id,
                name=name,
                age=age,
                student_class=student_class,
                roll_no=roll_no,
                email=email,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone
            )
            
            self.students[student_id] = student
            
            # Auto-save after adding
            self.save_data(backup=False)
            
            logger.info(f"Student added: {student.name}")
            return student
            
        except ValueError as e:
            logger.error(f"Failed to add student: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error adding student: {e}")
            return None
    
    def remove_student(self, student_id: str) -> bool:
        """
        Remove a student
        
        Args:
            student_id: Student ID
        
        Returns:
            bool: Success status
        """
        if student_id not in self.students:
            logger.warning(f"Student not found: {student_id}")
            return False
        
        student_name = self.students[student_id].name
        del self.students[student_id]
        
        # Auto-save after removal
        self.save_data(backup=False)
        
        logger.info(f"Student removed: {student_name}")
        return True
    
    # ========== TEACHER MANAGEMENT ==========
    def add_teacher(self, teacher_id: str, name: str, age: int, 
                   subject: str, salary: float, email: str = "") -> Optional[Teacher]:
        """
        Add a new teacher
        
        Args:
            teacher_id: Teacher ID
            name: Teacher name
            age: Teacher age
            subject: Teaching subject
            salary: Monthly salary
            email: Email (optional)
        
        Returns:
            Optional[Teacher]: Created teacher or None
        """
        try:
            if teacher_id in self.teachers:
                raise ValueError(f"Teacher ID {teacher_id} already exists")
            
            if salary <= 0:
                raise ValueError("Salary must be positive")
            
            teacher = Teacher(
                teacher_id=teacher_id,
                name=name,
                age=age,
                subject=subject,
                salary=salary,
                email=email
            )
            
            self.teachers[teacher_id] = teacher
            
            # Auto-save after adding
            self.save_data(backup=False)
            
            logger.info(f"Teacher added: {teacher.name}")
            return teacher
            
        except ValueError as e:
            logger.error(f"Failed to add teacher: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error adding teacher: {e}")
            return None
    
    # ========== ATTENDANCE MANAGEMENT ==========
    def mark_attendance_bulk(self, person_ids: List[str], 
                            status: AttendanceStatus,
                            person_type: str = "student") -> Dict[str, bool]:
        """
        Mark attendance for multiple persons
        
        Args:
            person_ids: List of person IDs
            status: Attendance status
            person_type: Type of person (student/teacher)
        
        Returns:
            Dict[str, bool]: Results for each person
        """
        results = {}
        today = datetime.date.today()
        
        for person_id in person_ids:
            try:
                if person_type == "student":
                    if person_id in self.students:
                        results[person_id] = self.students[person_id].mark_attendance(status, today)
                    else:
                        results[person_id] = False
                        logger.warning(f"Student not found: {person_id}")
                elif person_type == "teacher":
                    if person_id in self.teachers:
                        results[person_id] = self.teachers[person_id].mark_attendance(status, today)
                    else:
                        results[person_id] = False
                        logger.warning(f"Teacher not found: {person_id}")
                else:
                    results[person_id] = False
                    logger.error(f"Invalid person_type: {person_type}")
            except Exception as e:
                results[person_id] = False
                logger.error(f"Error marking attendance for {person_id}: {e}")
        
        # Auto-save after bulk attendance
        if any(results.values()):
            self.save_data(backup=False)
        
        logger.info(f"Bulk attendance marked: {sum(results.values())}/{len(person_ids)} successful")
        return results
    
    # ========== FINANCIAL MANAGEMENT ==========
    def collect_fees_bulk(self, fee_data: List[Dict]) -> Dict[str, bool]:
        """
        Collect fees from multiple students
        
        Args:
            fee_data: List of dictionaries with fee payment data
        
        Returns:
            Dict[str, bool]: Results for each student
        """
        results = {}
        
        for data in fee_data:
            student_id = data.get('student_id')
            amount = data.get('amount')
            method_str = data.get('method', 'Cash')
            
            if not student_id or not amount:
                results[student_id] = False
                continue
            
            try:
                method = PaymentMethod(method_str)
            except ValueError:
                logger.error(f"Invalid payment method: {method_str}")
                results[student_id] = False
                continue
            
            if student_id in self.students and amount:
                student = self.students[student_id]
                results[student_id] = student.pay_fees(amount, method)
            else:
                results[student_id] = False
                logger.warning(f"Student not found: {student_id}")
        
        # Auto-save after bulk fees collection
        if any(results.values()):
            self.save_data(backup=False)
        
        return results
    
    # ========== REPORTING ==========
    def generate_report(self, report_type: str, **kwargs) -> Dict[str, Any]:
        """
        Generate various reports
        
        Args:
            report_type: Type of report
            **kwargs: Report parameters
        
        Returns:
            Dict[str, Any]: Report data
        """
        if report_type == "student_summary":
            return self._generate_student_summary()
        elif report_type == "attendance_report":
            return self._generate_attendance_report(kwargs.get('date'))
        elif report_type == "financial_report":
            return self._generate_financial_report()
        elif report_type == "teacher_summary":
            return self._generate_teacher_summary()
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def _generate_student_summary(self) -> Dict[str, Any]:
        """Generate student summary report"""
        try:
            total_students = len(self.students)
            if total_students == 0:
                return {
                    'total_students': 0,
                    'students_by_class': {},
                    'avg_attendance': 0,
                    'total_fees_collected': 0,
                    'total_fees_due': 0
                }
            
            total_attendance = sum(s.get_attendance_percentage() 
                                 for s in self.students.values())
            avg_attendance = total_attendance / total_students
            
            total_fees_collected = sum(s.fees_paid for s in self.students.values())
            total_fees_due = sum(max(s.fees_due, 0) for s in self.students.values())  # Ensure non-negative
            
            return {
                'total_students': total_students,
                'students_by_class': self._group_students_by_class(),
                'avg_attendance': avg_attendance,
                'total_fees_collected': total_fees_collected,
                'total_fees_due': total_fees_due
            }
        except Exception as e:
            logger.error(f"Error generating student summary: {e}")
            return {
                'total_students': 0,
                'students_by_class': {},
                'avg_attendance': 0,
                'total_fees_collected': 0,
                'total_fees_due': 0
            }
    
    def _group_students_by_class(self) -> Dict[str, int]:
        """Group students by their class"""
        classes = {}
        for student in self.students.values():
            if student.student_class:
                classes[student.student_class] = classes.get(student.student_class, 0) + 1
        return classes
    
    def _generate_attendance_report(self, date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """Generate attendance report"""
        if date is None:
            date = datetime.date.today()
        
        date_str = date.strftime(Config.DATE_FORMAT)
        
        student_attendance = {}
        present_count = 0
        
        for student in self.students.values():
            status = student.attendance.get(date_str, "Not Marked")
            if status == "Present":
                present_count += 1
            student_attendance[student.person_id] = {
                'name': student.name,
                'status': status,
                'class': student.student_class
            }
        
        total_students = len(student_attendance)
        attendance_percentage = (present_count / total_students * 100) if total_students > 0 else 0
        
        return {
            'date': date_str,
            'student_attendance': student_attendance,
            'present_count': present_count,
            'total_students': total_students,
            'attendance_percentage': attendance_percentage
        }
    
    def _generate_financial_report(self) -> Dict[str, Any]:
        """Generate financial report"""
        try:
            total_salary_paid = 0
            for teacher in self.teachers.values():
                for payment in teacher.salary_payments:
                    total_salary_paid += payment.get('net_salary', 0)
            
            total_fees_collected = sum(s.fees_paid for s in self.students.values())
            total_fees_due = sum(max(s.fees_due, 0) for s in self.students.values())
            
            total_fees = total_fees_collected + total_fees_due
            collection_rate = (total_fees_collected / total_fees * 100) if total_fees > 0 else 0
            
            monthly_salary_commitment = sum(t.salary for t in self.teachers.values())
            
            return {
                'student_fees': {
                    'total_collected': total_fees_collected,
                    'total_due': total_fees_due,
                    'collection_rate': collection_rate
                },
                'salary_expenses': {
                    'total_paid': total_salary_paid,
                    'monthly_salary_commitment': monthly_salary_commitment,
                    'teachers_count': len(self.teachers)
                },
                'net_balance': total_fees_collected - total_salary_paid
            }
        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return {
                'student_fees': {'total_collected': 0, 'total_due': 0, 'collection_rate': 0},
                'salary_expenses': {'total_paid': 0, 'monthly_salary_commitment': 0, 'teachers_count': 0},
                'net_balance': 0
            }
    
    def _generate_teacher_summary(self) -> Dict[str, Any]:
        """Generate teacher summary report"""
        try:
            total_teachers = len(self.teachers)
            if total_teachers == 0:
                return {
                    'total_teachers': 0,
                    'teachers_by_subject': {},
                    'avg_experience': 0,
                    'total_salary_commitment': 0
                }
            
            total_experience = sum(t.experience_years for t in self.teachers.values())
            avg_experience = total_experience / total_teachers
            total_salary_commitment = sum(t.salary for t in self.teachers.values())
            
            return {
                'total_teachers': total_teachers,
                'teachers_by_subject': self._group_teachers_by_subject(),
                'avg_experience': avg_experience,
                'total_salary_commitment': total_salary_commitment
            }
        except Exception as e:
            logger.error(f"Error generating teacher summary: {e}")
            return {
                'total_teachers': 0,
                'teachers_by_subject': {},
                'avg_experience': 0,
                'total_salary_commitment': 0
            }
    
    # ========== STATISTICS ==========
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            return {
                'students': {
                    'total': len(self.students),
                    'by_class': self._group_students_by_class(),
                    'avg_age': sum(s.age for s in self.students.values()) / max(len(self.students), 1)
                },
                'teachers': {
                    'total': len(self.teachers),
                    'by_subject': self._group_teachers_by_subject(),
                    'avg_experience': sum(t.experience_years for t in self.teachers.values()) / max(len(self.teachers), 1)
                },
                'attendance': {
                    'student_avg': sum(s.get_attendance_percentage() 
                                     for s in self.students.values()) / max(len(self.students), 1)
                },
                'financial': self._generate_financial_report()
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'students': {'total': 0, 'by_class': {}, 'avg_age': 0},
                'teachers': {'total': 0, 'by_subject': {}, 'avg_experience': 0},
                'attendance': {'student_avg': 0},
                'financial': {
                    'student_fees': {'total_collected': 0, 'total_due': 0, 'collection_rate': 0},
                    'salary_expenses': {'total_paid': 0, 'monthly_salary_commitment': 0, 'teachers_count': 0},
                    'net_balance': 0
                }
            }
    
    def _group_teachers_by_subject(self) -> Dict[str, int]:
        """Group teachers by subject"""
        subjects = {}
        for teacher in self.teachers.values():
            if teacher.subject:
                subjects[teacher.subject] = subjects.get(teacher.subject, 0) + 1
        return subjects
    
    def __str__(self) -> str:
        return f"SchoolManagementSystem(students={len(self.students)}, teachers={len(self.teachers)})"


# ============================================
# 🎯 CLI INTERFACE (FIXED)
# ============================================
class SchoolCLI:
    """Command Line Interface for the School Management System"""
    
    def __init__(self):
        self.system = SchoolManagementSystem()
        self.running = True
    
    def display_banner(self):
        """Display welcome banner"""
        print("\n" + "="*60)
        print("🏫 PROFESSIONAL SCHOOL MANAGEMENT SYSTEM")
        print("="*60)
        print("Features:")
        print("  • Student & Teacher Management")
        print("  • Attendance Tracking with datetime")
        print("  • Fees & Salary System")
        print("  • File Handling & Data Persistence")
        print("  • Comprehensive Reporting")
        print("="*60)
        print("GitHub Ready • LinkedIn Showcase • Production Grade")
        print("="*60 + "\n")
    
    def display_menu(self):
        """Display main menu"""
        menu_options = [
            ("1", "📝 Student Management"),
            ("2", "👩‍🏫 Teacher Management"),
            ("3", "📅 Attendance System"),
            ("4", "💰 Financial Management"),
            ("5", "📊 Reports & Analytics"),
            ("6", "💾 Data Operations"),
            ("7", "⚙️  System Information"),
            ("8", "🚪 Exit")
        ]
        
        print("\n" + "="*50)
        print("MAIN MENU")
        print("="*50)
        for num, desc in menu_options:
            print(f"{num}. {desc}")
        print("="*50)
    
    def handle_student_management(self):
        """Handle student management operations"""
        while True:
            print("\n" + "="*40)
            print("📝 STUDENT MANAGEMENT")
            print("="*40)
            print("1. Add New Student")
            print("2. View All Students")
            print("3. Search Student")
            print("4. Update Student")
            print("5. Mark Attendance")
            print("6. Pay Fees")
            print("7. View Student Details")
            print("8. Back to Main Menu")
            print("="*40)
            
            choice = input("\nEnter choice (1-8): ").strip()
            
            if choice == '1':
                self.add_student()
            elif choice == '2':
                self.view_all_students()
            elif choice == '3':
                self.search_student()
            elif choice == '4':
                self.update_student()
            elif choice == '5':
                self.mark_student_attendance()
            elif choice == '6':
                self.pay_student_fees()
            elif choice == '7':
                self.view_student_details()
            elif choice == '8':
                break
            else:
                print("❌ Invalid choice!")
    
    def add_student(self):
        """Add a new student"""
        print("\n" + "="*40)
        print("➕ ADD NEW STUDENT")
        print("="*40)
        
        try:
            # Get all inputs
            student_id = input("Student ID: ").strip()
            name = input("Full Name: ").strip()
            age = int(input("Age: ").strip())
            student_class = input("Class: ").strip()
            roll_no = int(input("Roll Number: ").strip())
            email = input("Email (optional): ").strip()
            guardian_name = input("Guardian Name (optional): ").strip()
            guardian_phone = input("Guardian Phone (optional): ").strip()
            
            # Call the fixed add_student method
            student = self.system.add_student(
                student_id=student_id,
                name=name,
                age=age,
                student_class=student_class,
                roll_no=roll_no,
                email=email,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone
            )
            
            if student:
                print(f"\n✅ Student added successfully!")
                print(student.display_info())
        except ValueError as e:
            print(f"❌ Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    def view_all_students(self):
        """View all students"""
        if not self.system.students:
            print("\n📭 No students found!")
            return
        
        print(f"\n📚 ALL STUDENTS ({len(self.system.students)} total)")
        print("="*60)
        
        for i, (student_id, student) in enumerate(self.system.students.items(), 1):
            print(f"\n{i}. {student.name}")
            print(f"   ID: {student_id}")
            print(f"   Class: {student.student_class}, Roll: {student.roll_no}")
            print(f"   Attendance: {student.get_attendance_percentage():.1f}%")
            print(f"   Fees: Paid ₹{student.fees_paid:,.2f}, Due ₹{student.fees_due:,.2f}")
        
        print("\n" + "="*60)
    
    def search_student(self):
        """Search for a student"""
        search_term = input("\n🔍 Enter student ID or name: ").strip().lower()
        
        if not search_term:
            print("❌ Please enter a search term")
            return
        
        results = []
        for student_id, student in self.system.students.items():
            if (search_term in student_id.lower() or 
                search_term in student.name.lower()):
                results.append((student_id, student))
        
        if not results:
            print("❌ No students found!")
            return
        
        print(f"\n📋 Found {len(results)} student(s):")
        for i, (student_id, student) in enumerate(results, 1):
            print(f"\n{i}. {student.display_info()}")
    
    def update_student(self):
        """Update student information"""
        student_id = input("\nEnter student ID to update: ").strip()
        
        if not student_id:
            print("❌ Please enter student ID")
            return
        
        if student_id not in self.system.students:
            print("❌ Student not found!")
            return
        
        student = self.system.students[student_id]
        print(f"\nUpdating student: {student.name}")
        
        # Get new values
        updates = {}
        name = input(f"Name [{student.name}]: ").strip()
        if name:
            updates['name'] = name
        
        age_input = input(f"Age [{student.age}]: ").strip()
        if age_input:
            try:
                updates['age'] = int(age_input)
            except ValueError:
                print("❌ Invalid age format")
                return
        
        student_class = input(f"Class [{student.student_class}]: ").strip()
        if student_class:
            updates['student_class'] = student_class
        
        email = input(f"Email [{student.email}]: ").strip()
        if email:
            updates['email'] = email
        
        # Update guardian information
        guardian_name = input(f"Guardian Name [{student.guardian_name}]: ").strip()
        if guardian_name:
            student.guardian_name = guardian_name
        
        guardian_phone = input(f"Guardian Phone [{student.guardian_phone}]: ").strip()
        if guardian_phone:
            student.guardian_phone = guardian_phone
        
        if updates:
            try:
                student.update(**updates)
                print("✅ Student updated successfully!")
                # Auto-save
                self.system.save_data(backup=False)
            except ValueError as e:
                print(f"❌ Error updating student: {e}")
        elif guardian_name or guardian_phone:
            print("✅ Guardian information updated successfully!")
            self.system.save_data(backup=False)
        else:
            print("⚠️  No changes made.")
    
    def mark_student_attendance(self):
        """Mark student attendance"""
        print("\n" + "="*40)
        print("📅 MARK STUDENT ATTENDANCE")
        print("="*40)
        
        print("\nAttendance Status Options:")
        for status in AttendanceStatus:
            print(f"  {status.value}")
        
        status_input = input("\nEnter status: ").strip()
        if not status_input:
            print("❌ Please enter status")
            return
        
        try:
            status = AttendanceStatus(status_input)
        except ValueError:
            print("❌ Invalid status! Please use one of the options above.")
            return
        
        student_id = input("Enter student ID: ").strip()
        if not student_id:
            print("❌ Please enter student ID")
            return
        
        if student_id not in self.system.students:
            print("❌ Student not found!")
            return
        
        student = self.system.students[student_id]
        if student.mark_attendance(status):
            print(f"✅ Attendance marked for {student.name}")
            # Auto-save
            self.system.save_data(backup=False)
        else:
            print(f"❌ Failed to mark attendance for {student.name}")
    
    def pay_student_fees(self):
        """Pay student fees"""
        student_id = input("\nEnter student ID: ").strip()
        
        if not student_id:
            print("❌ Please enter student ID")
            return
        
        if student_id not in self.system.students:
            print("❌ Student not found!")
            return
        
        student = self.system.students[student_id]
        print(f"\nStudent: {student.name}")
        print(f"Fees Due: ₹{student.fees_due:,.2f}")
        
        if student.fees_due <= 0:
            print("✅ No fees due!")
            return
        
        try:
            amount_input = input("\nEnter payment amount: ₹").strip()
            if not amount_input:
                print("❌ Please enter amount")
                return
            
            amount = float(amount_input)
            
            print("\nPayment Methods:")
            for method in PaymentMethod:
                print(f"  {method.value}")
            
            method_input = input("\nEnter payment method: ").strip()
            if not method_input:
                print("❌ Please enter payment method")
                return
            
            method = PaymentMethod(method_input)
            
            description = input("Payment description (optional): ").strip()
            
            if student.pay_fees(amount, method, description):
                print("✅ Payment successful!")
                # Auto-save
                self.system.save_data(backup=False)
            else:
                print("❌ Payment failed!")
                
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    def view_student_details(self):
        """View detailed student information"""
        student_id = input("\nEnter student ID: ").strip()
        
        if not student_id:
            print("❌ Please enter student ID")
            return
        
        if student_id not in self.system.students:
            print("❌ Student not found!")
            return
        
        student = self.system.students[student_id]
        print(student.display_info(detailed=True))
    
    def handle_teacher_management(self):
        """Handle teacher management operations"""
        while True:
            print("\n" + "="*40)
            print("👩‍🏫 TEACHER MANAGEMENT")
            print("="*40)
            print("1. Add New Teacher")
            print("2. View All Teachers")
            print("3. Pay Salary")
            print("4. View Teacher Details")
            print("5. Update Teacher")
            print("6. Back to Main Menu")
            print("="*40)
            
            choice = input("\nEnter choice (1-6): ").strip()
            
            if choice == '1':
                self.add_teacher()
            elif choice == '2':
                self.view_all_teachers()
            elif choice == '3':
                self.pay_teacher_salary()
            elif choice == '4':
                self.view_teacher_details()
            elif choice == '5':
                self.update_teacher()
            elif choice == '6':
                break
            else:
                print("❌ Invalid choice!")
    
    def add_teacher(self):
        """Add a new teacher"""
        print("\n" + "="*40)
        print("➕ ADD NEW TEACHER")
        print("="*40)
        
        try:
            # Get all inputs
            teacher_id = input("Teacher ID: ").strip()
            name = input("Full Name: ").strip()
            age = int(input("Age: ").strip())
            subject = input("Subject: ").strip()
            salary = float(input("Monthly Salary: ₹").strip())
            email = input("Email (optional): ").strip()
            qualification = input("Qualification (optional): ").strip()
            experience_years = int(input("Experience (years, optional): ").strip() or "0")
            
            # Create teacher
            teacher = self.system.add_teacher(
                teacher_id=teacher_id,
                name=name,
                age=age,
                subject=subject,
                salary=salary,
                email=email
            )
            
            if teacher:
                # Set optional fields
                if qualification:
                    teacher.qualification = qualification
                if experience_years:
                    teacher.experience_years = experience_years
                
                print(f"\n✅ Teacher added successfully!")
                print(teacher.display_info())
        except ValueError as e:
            print(f"❌ Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    def view_all_teachers(self):
        """View all teachers"""
        if not self.system.teachers:
            print("\n📭 No teachers found!")
            return
        
        print(f"\n👩‍🏫 ALL TEACHERS ({len(self.system.teachers)} total)")
        print("="*60)
        
        for i, (teacher_id, teacher) in enumerate(self.system.teachers.items(), 1):
            print(f"\n{i}. {teacher.name}")
            print(f"   ID: {teacher_id}")
            print(f"   Subject: {teacher.subject}")
            print(f"   Salary: ₹{teacher.salary:,.2f}/month")
            print(f"   Experience: {teacher.experience_years} years")
        
        print("\n" + "="*60)
    
    def pay_teacher_salary(self):
        """Pay teacher salary"""
        teacher_id = input("\nEnter teacher ID: ").strip()
        
        if not teacher_id:
            print("❌ Please enter teacher ID")
            return
        
        if teacher_id not in self.system.teachers:
            print("❌ Teacher not found!")
            return
        
        teacher = self.system.teachers[teacher_id]
        print(f"\nTeacher: {teacher.name}")
        print(f"Monthly Salary: ₹{teacher.salary:,.2f}")
        
        try:
            bonus_input = input("Bonus amount (₹0 for no bonus): ₹").strip() or "0"
            deductions_input = input("Deductions amount (₹0 for no deductions): ₹").strip() or "0"
            
            bonus = float(bonus_input)
            deductions = float(deductions_input)
            
            if teacher.receive_salary(bonus, deductions):
                print("✅ Salary paid successfully!")
                # Auto-save
                self.system.save_data(backup=False)
            else:
                print("❌ Salary payment failed!")
                
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    def view_teacher_details(self):
        """View detailed teacher information"""
        teacher_id = input("\nEnter teacher ID: ").strip()
        
        if not teacher_id:
            print("❌ Please enter teacher ID")
            return
        
        if teacher_id not in self.system.teachers:
            print("❌ Teacher not found!")
            return
        
        teacher = self.system.teachers[teacher_id]
        print(teacher.display_info(detailed=True))
    
    def update_teacher(self):
        """Update teacher information"""
        teacher_id = input("\nEnter teacher ID to update: ").strip()
        
        if not teacher_id:
            print("❌ Please enter teacher ID")
            return
        
        if teacher_id not in self.system.teachers:
            print("❌ Teacher not found!")
            return
        
        teacher = self.system.teachers[teacher_id]
        print(f"\nUpdating teacher: {teacher.name}")
        
        # Get new values
        updates = {}
        name = input(f"Name [{teacher.name}]: ").strip()
        if name:
            updates['name'] = name
        
        age_input = input(f"Age [{teacher.age}]: ").strip()
        if age_input:
            try:
                updates['age'] = int(age_input)
            except ValueError:
                print("❌ Invalid age format")
                return
        
        subject = input(f"Subject [{teacher.subject}]: ").strip()
        if subject:
            updates['subject'] = subject
        
        salary_input = input(f"Salary [{teacher.salary}]: ").strip()
        if salary_input:
            try:
                updates['salary'] = float(salary_input)
            except ValueError:
                print("❌ Invalid salary format")
                return
        
        email = input(f"Email [{teacher.email}]: ").strip()
        if email:
            updates['email'] = email
        
        # Update optional fields
        qualification = input(f"Qualification [{teacher.qualification}]: ").strip()
        if qualification:
            teacher.qualification = qualification
        
        experience_input = input(f"Experience years [{teacher.experience_years}]: ").strip()
        if experience_input:
            try:
                teacher.experience_years = int(experience_input)
            except ValueError:
                print("❌ Invalid experience format")
        
        if updates:
            try:
                teacher.update(**updates)
                print("✅ Teacher updated successfully!")
                # Auto-save
                self.system.save_data(backup=False)
            except ValueError as e:
                print(f"❌ Error updating teacher: {e}")
        elif qualification or experience_input:
            print("✅ Teacher updated successfully!")
            self.system.save_data(backup=False)
        else:
            print("⚠️  No changes made.")
    
    def handle_attendance_system(self):
        """Handle attendance system operations"""
        while True:
            print("\n" + "="*40)
            print("📅 ATTENDANCE SYSTEM")
            print("="*40)
            print("1. Mark Bulk Attendance")
            print("2. View Attendance Report")
            print("3. View Attendance Analytics")
            print("4. Back to Main Menu")
            print("="*40)
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == '1':
                self.mark_bulk_attendance()
            elif choice == '2':
                self.view_attendance_report()
            elif choice == '3':
                self.show_attendance_analytics()
            elif choice == '4':
                return
            else:
                print("❌ Invalid choice!")
    
    def mark_bulk_attendance(self):
        """Mark attendance in bulk"""
        print("\n" + "="*40)
        print("📝 BULK ATTENDANCE")
        print("="*40)
        
        print("\nFor whom to mark attendance?")
        print("1. Students")
        print("2. Teachers")
        person_type_choice = input("\nEnter choice (1-2): ").strip()
        
        if person_type_choice == '1':
            person_type_str = "student"
            persons = self.system.students
        elif person_type_choice == '2':
            person_type_str = "teacher"
            persons = self.system.teachers
        else:
            print("❌ Invalid choice!")
            return
        
        if not persons:
            print(f"📭 No {person_type_str}s found!")
            return
        
        print("\nAttendance Status Options:")
        for status in AttendanceStatus:
            print(f"  {status.value}")
        
        status_input = input("\nEnter status: ").strip()
        if not status_input:
            print("❌ Please enter status")
            return
        
        try:
            status = AttendanceStatus(status_input)
        except ValueError:
            print("❌ Invalid status!")
            return
        
        # Confirm marking for all
        print(f"\nMark attendance for ALL {len(persons)} {person_type_str}s as {status.value}?")
        confirm = input("Type 'YES' to confirm: ").strip()
        
        if confirm != 'YES':
            print("❌ Operation cancelled")
            return
        
        # Mark for all persons
        person_ids = list(persons.keys())
        results = self.system.mark_attendance_bulk(person_ids, status, person_type_str)
        
        successful = sum(results.values())
        print(f"\n✅ Attendance marked for {successful}/{len(person_ids)} {person_type_str}s")
    
    def view_attendance_report(self):
        """View attendance report"""
        date_str = input("\nEnter date (YYYY-MM-DD) or press Enter for today: ").strip()
        
        try:
            if date_str:
                date = datetime.datetime.strptime(date_str, Config.DATE_FORMAT).date()
            else:
                date = datetime.date.today()
            
            report = self.system.generate_report("attendance_report", date=date)
            
            print(f"\n📊 ATTENDANCE REPORT - {report['date']}")
            print("="*60)
            print(f"{'Name':<20} {'Class':<10} {'Status':<10}")
            print("-"*60)
            
            for student_id, data in report['student_attendance'].items():
                print(f"{data['name']:<20} {data['class']:<10} {data['status']:<10}")
            
            print("-"*60)
            present_count = report.get('present_count', 0)
            total_students = report.get('total_students', 0)
            print(f"Present: {present_count}/{total_students}")
            
            if total_students > 0:
                percentage = (present_count / total_students) * 100
                print(f"Percentage: {percentage:.1f}%")
            
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    def handle_financial_management(self):
        """Handle financial management operations"""
        while True:
            print("\n" + "="*40)
            print("💰 FINANCIAL MANAGEMENT")
            print("="*40)
            print("1. Financial Report")
            print("2. Collect Bulk Fees")
            print("3. Pay Bulk Salaries")
            print("4. View Student Fees Summary")
            print("5. Back to Main Menu")
            print("="*40)
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                self.show_financial_report()
            elif choice == '2':
                self.collect_bulk_fees()
            elif choice == '3':
                self.pay_bulk_salaries()
            elif choice == '4':
                self.view_student_fees_summary()
            elif choice == '5':
                return
            else:
                print("❌ Invalid choice!")
    
    def show_financial_report(self):
        """Show financial report"""
        report = self.system.generate_report("financial_report")
        
        print("\n" + "="*60)
        print("💰 FINANCIAL REPORT")
        print("="*60)
        
        print("\n📈 STUDENT FEES:")
        fees = report['student_fees']
        print(f"  Total Collected: ₹{fees['total_collected']:,.2f}")
        print(f"  Total Due: ₹{fees['total_due']:,.2f}")
        print(f"  Collection Rate: {fees.get('collection_rate', 0):.1f}%")
        
        print("\n💸 SALARY EXPENSES:")
        salary = report['salary_expenses']
        print(f"  Total Paid: ₹{salary['total_paid']:,.2f}")
        print(f"  Monthly Commitment: ₹{salary['monthly_salary_commitment']:,.2f}")
        print(f"  Number of Teachers: {salary['teachers_count']}")
        
        print(f"\n💰 NET BALANCE: ₹{report.get('net_balance', 0):,.2f}")
        print("="*60)
    
    def collect_bulk_fees(self):
        """Collect fees in bulk"""
        print("\n" + "="*40)
        print("💰 BULK FEE COLLECTION")
        print("="*40)
        
        fee_data = []
        while True:
            print(f"\nEnter fee payment {len(fee_data) + 1}:")
            student_id = input("Student ID (or 'done' to finish): ").strip()
            
            if student_id.lower() == 'done':
                break
            
            if not student_id:
                print("❌ Please enter student ID")
                continue
            
            if student_id not in self.system.students:
                print("❌ Student not found!")
                continue
            
            try:
                amount_input = input("Amount: ₹").strip()
                if not amount_input:
                    print("❌ Please enter amount")
                    continue
                
                amount = float(amount_input)
                
                print("\nPayment Methods:")
                for method in PaymentMethod:
                    print(f"  {method.value}")
                
                method_input = input("\nPayment method: ").strip()
                if not method_input:
                    print("❌ Please enter payment method")
                    continue
                
                method = PaymentMethod(method_input)
                
                fee_data.append({
                    'student_id': student_id,
                    'amount': amount,
                    'method': method.value
                })
                
                print("✅ Added to batch")
                
            except (ValueError, KeyError) as e:
                print(f"❌ Error: {e}")
        
        if fee_data:
            results = self.system.collect_fees_bulk(fee_data)
            successful = sum(results.values())
            print(f"\n✅ Processed {successful}/{len(fee_data)} payments successfully!")
        else:
            print("\n⚠️  No payments to process")
    
    def pay_bulk_salaries(self):
        """Pay salaries in bulk"""
        if not self.system.teachers:
            print("\n📭 No teachers found!")
            return
        
        print("\n" + "="*40)
        print("💰 BULK SALARY PAYMENT")
        print("="*40)
        
        successful = 0
        for teacher_id, teacher in self.system.teachers.items():
            print(f"\nPay salary to {teacher.name}?")
            print(f"Monthly Salary: ₹{teacher.salary:,.2f}")
            
            choice = input("Pay salary? (y/n): ").strip().lower()
            
            if choice == 'y':
                try:
                    bonus_input = input(f"Bonus for {teacher.name} (₹0 for no bonus): ₹").strip() or "0"
                    deductions_input = input(f"Deductions for {teacher.name} (₹0 for no deductions): ₹").strip() or "0"
                    
                    bonus = float(bonus_input)
                    deductions = float(deductions_input)
                    
                    if teacher.receive_salary(bonus, deductions):
                        successful += 1
                        print(f"✅ Salary paid to {teacher.name}")
                    else:
                        print(f"❌ Failed to pay {teacher.name}")
                        
                except ValueError as e:
                    print(f"❌ Error: {e}")
            elif choice == 'n':
                print(f"⏭️  Skipped {teacher.name}")
            else:
                print(f"❌ Invalid choice, skipping {teacher.name}")
        
        if successful > 0:
            # Auto-save
            self.system.save_data(backup=False)
            print(f"\n✅ Paid salaries to {successful}/{len(self.system.teachers)} teachers")
    
    def view_student_fees_summary(self):
        """View fees summary for a student"""
        student_id = input("\nEnter student ID: ").strip()
        
        if not student_id:
            print("❌ Please enter student ID")
            return
        
        if student_id not in self.system.students:
            print("❌ Student not found!")
            return
        
        student = self.system.students[student_id]
        summary = student.get_fees_summary()
        
        print(f"\n💰 FEES SUMMARY FOR {student.name.upper()}")
        print("="*50)
        print(f"Total Fees: ₹{summary['total_fees']:,.2f}")
        print(f"Fees Paid: ₹{summary['fees_paid']:,.2f}")
        print(f"Fees Due: ₹{summary['fees_due']:,.2f}")
        print(f"Payment Progress: {summary['payment_percentage']:.1f}%")
        print(f"Total Transactions: {summary['total_transactions']}")
        
        if summary['last_payment']:
            last_payment_date = summary['last_payment'].strftime(Config.DATE_FORMAT)
            print(f"Last Payment: {last_payment_date}")
        
        print("="*50)
    
    def handle_reports(self):
        """Handle reports and analytics"""
        while True:
            print("\n" + "="*40)
            print("📊 REPORTS & ANALYTICS")
            print("="*40)
            print("1. System Statistics")
            print("2. Student Summary Report")
            print("3. Teacher Summary Report")
            print("4. Attendance Analytics")
            print("5. Back to Main Menu")
            print("="*40)
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                self.show_system_statistics()
            elif choice == '2':
                self.show_student_summary()
            elif choice == '3':
                self.show_teacher_summary()
            elif choice == '4':
                self.show_attendance_analytics()
            elif choice == '5':
                return
            else:
                print("❌ Invalid choice!")
    
    def show_system_statistics(self):
        """Show system statistics"""
        stats = self.system.get_statistics()
        
        print("\n" + "="*60)
        print("📊 SYSTEM STATISTICS")
        print("="*60)
        
        print(f"\n🎓 STUDENTS ({stats['students']['total']} total):")
        print(f"  Average Age: {stats['students']['avg_age']:.1f} years")
        print("  Distribution by Class:")
        for class_name, count in stats['students']['by_class'].items():
            percentage = (count / stats['students']['total'] * 100) if stats['students']['total'] > 0 else 0
            print(f"    {class_name}: {count} students ({percentage:.1f}%)")
        
        print(f"\n👩‍🏫 TEACHERS ({stats['teachers']['total']} total):")
        print(f"  Average Experience: {stats['teachers']['avg_experience']:.1f} years")
        print("  Distribution by Subject:")
        for subject, count in stats['teachers']['by_subject'].items():
            percentage = (count / stats['teachers']['total'] * 100) if stats['teachers']['total'] > 0 else 0
            print(f"    {subject}: {count} teachers ({percentage:.1f}%)")
        
        print(f"\n📅 ATTENDANCE:")
        print(f"  Student Average: {stats['attendance']['student_avg']:.1f}%")
        
        print("\n💰 FINANCIAL SUMMARY:")
        financial = stats['financial']
        print(f"  Net Balance: ₹{financial.get('net_balance', 0):,.2f}")
        
        print("="*60)
    
    def show_student_summary(self):
        """Show student summary report"""
        report = self.system.generate_report("student_summary")
        
        print("\n" + "="*60)
        print("🎓 STUDENT SUMMARY REPORT")
        print("="*60)
        
        print(f"\nTotal Students: {report['total_students']}")
        
        if report['total_students'] > 0:
            print("\nDistribution by Class:")
            for class_name, count in report['students_by_class'].items():
                percentage = (count / report['total_students']) * 100
                print(f"  {class_name}: {count} students ({percentage:.1f}%)")
            
            print(f"\n📊 Academic Performance:")
            print(f"  Average Attendance: {report.get('avg_attendance', 0):.1f}%")
            
            print(f"\n💰 Financial Status:")
            print(f"  Total Fees Collected: ₹{report.get('total_fees_collected', 0):,.2f}")
            print(f"  Total Fees Due: ₹{report.get('total_fees_due', 0):,.2f}")
            
            total_fees = report.get('total_fees_collected', 0) + report.get('total_fees_due', 0)
            if total_fees > 0:
                collection_rate = (report.get('total_fees_collected', 0) / total_fees) * 100
                print(f"  Collection Rate: {collection_rate:.1f}%")
        
        print("="*60)
    
    def show_teacher_summary(self):
        """Show teacher summary report"""
        report = self.system.generate_report("teacher_summary")
        
        print("\n" + "="*60)
        print("👩‍🏫 TEACHER SUMMARY REPORT")
        print("="*60)
        
        print(f"\nTotal Teachers: {report['total_teachers']}")
        
        if report['total_teachers'] > 0:
            print("\nDistribution by Subject:")
            for subject, count in report['teachers_by_subject'].items():
                percentage = (count / report['total_teachers']) * 100
                print(f"  {subject}: {count} teachers ({percentage:.1f}%)")
            
            print(f"\n📊 Professional Information:")
            print(f"  Average Experience: {report.get('avg_experience', 0):.1f} years")
            
            print(f"\n💰 Financial Status:")
            print(f"  Total Monthly Salary Commitment: ₹{report.get('total_salary_commitment', 0):,.2f}")
        
        print("="*60)
    
    def show_attendance_analytics(self):
        """Show attendance analytics"""
        print("\n" + "="*40)
        print("📈 ATTENDANCE ANALYTICS")
        print("="*40)
        
        # Get month and year for analysis
        month_input = input("Enter month (1-12, or Enter for all): ").strip()
        year_input = input("Enter year (YYYY, or Enter for current): ").strip()
        
        try:
            month = int(month_input) if month_input else None
            year = int(year_input) if year_input else datetime.date.today().year
            
            if month is not None and (month < 1 or month > 12):
                print("❌ Month must be between 1 and 12")
                return
            
            print(f"\nAttendance Analysis for {f'Month {month}, ' if month else ''}{year}")
            print("-"*60)
            print(f"{'Name':<20} {'Class':<10} {'Attendance':>10}")
            print("-"*60)
            
            total_percentage = 0
            student_count = 0
            
            for student in self.system.students.values():
                percentage = student.get_attendance_percentage(month, year)
                total_percentage += percentage
                student_count += 1
                
                print(f"{student.name:<20} {student.student_class:<10} {percentage:>9.1f}%")
            
            if student_count > 0:
                print("-"*60)
                overall_avg = total_percentage / student_count
                print(f"Overall Average: {overall_avg:>30.1f}%")
            
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    def handle_data_operations(self):
        """Handle data operations"""
        while True:
            print("\n" + "="*40)
            print("💾 DATA OPERATIONS")
            print("="*40)
            print("1. Save Data")
            print("2. Create Backup")
            print("3. Load Data")
            print("4. Restore from Backup")
            print("5. View Data Info")
            print("6. Back to Main Menu")
            print("="*40)
            
            choice = input("\nEnter choice (1-6): ").strip()
            
            if choice == '1':
                if self.system.save_data(backup=False):
                    print("✅ Data saved successfully!")
                else:
                    print("❌ Failed to save data!")
            elif choice == '2':
                if self.system.save_data(backup=True):
                    print("✅ Backup created successfully!")
                else:
                    print("❌ Failed to create backup!")
            elif choice == '3':
                if self.system.load_data():
                    print("✅ Data loaded successfully!")
                else:
                    print("❌ Failed to load data!")
            elif choice == '4':
                if self.system.restore_from_backup():
                    print("✅ Data restored from backup!")
                else:
                    print("❌ Failed to restore from backup!")
            elif choice == '5':
                self.show_data_info()
            elif choice == '6':
                return
            else:
                print("❌ Invalid choice!")
    
    def show_data_info(self):
        """Show data information"""
        print("\n" + "="*40)
        print("📁 DATA INFORMATION")
        print("="*40)
        
        print(f"\n📊 Current Data in Memory:")
        print(f"  Students: {len(self.system.students)}")
        print(f"  Teachers: {len(self.system.teachers)}")
        
        data_file = self.system.config.DATA_FILE
        if os.path.exists(data_file):
            file_size = os.path.getsize(data_file)
            print(f"\n💾 Data File: {data_file}")
            print(f"  Size: {file_size:,} bytes")
            print(f"  Last Modified: {datetime.datetime.fromtimestamp(os.path.getmtime(data_file)).strftime(Config.DATETIME_FORMAT)}")
            
            # Count backups
            backup_dir = self.system.config.BACKUP_DIR
            if os.path.exists(backup_dir):
                backups = [f for f in os.listdir(backup_dir) if f.endswith('.pkl')]
                print(f"  Backups: {len(backups)} files")
                if backups:
                    # Show latest backup
                    backups.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
                    latest_backup = backups[0]
                    backup_time = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(backup_dir, latest_backup)))
                    print(f"  Latest Backup: {latest_backup} ({backup_time.strftime(Config.DATETIME_FORMAT)})")
        else:
            print(f"\n❌ Data file not found: {data_file}")
        
        print("="*40)
    
    def show_system_info(self):
        """Show system information"""
        print("\n" + "="*60)
        print("⚙️  SYSTEM INFORMATION")
        print("="*60)
        
        print("\n🏫 SCHOOL MANAGEMENT SYSTEM")
        print("Version: 2.0.0")
        print("Features:")
        features = [
            "✓ Object-Oriented Design with Inheritance",
            "✓ Student & Teacher Management",
            "✓ Attendance Tracking with datetime",
            "✓ Fees & Salary System",
            "✓ Exception Handling & Data Validation",
            "✓ File Handling & Data Persistence",
            "✓ Comprehensive Reporting",
            "✓ Logging System",
            "✓ CLI Interface",
            "✓ Backup & Restore System",
            "✓ Data Validation & Error Handling",
            "✓ Auto-save Functionality"
        ]
        
        for feature in features:
            print(f"  {feature}")
        
        print("\n📊 CURRENT STATISTICS:")
        print(f"  Students: {len(self.system.students)}")
        print(f"  Teachers: {len(self.system.teachers)}")
        
        print("\n💡 TECHNOLOGIES USED:")
        print("  • Python 3.8+")
        print("  • Object-Oriented Programming")
        print("  • File Handling (Pickle)")
        print("  • datetime Module")
        print("  • Logging Module")
        print("  • Type Hints")
        print("  • Data Classes")
        
        print("="*60)
        
        input("\nPress Enter to continue...")
    
    def run(self):
        """Run the CLI application"""
        self.display_banner()
        
        while self.running:
            try:
                self.display_menu()
                choice = input("\nEnter your choice (1-8): ").strip()
                
                if choice == '1':
                    self.handle_student_management()
                elif choice == '2':
                    self.handle_teacher_management()
                elif choice == '3':
                    self.handle_attendance_system()
                elif choice == '4':
                    self.handle_financial_management()
                elif choice == '5':
                    self.handle_reports()
                elif choice == '6':
                    self.handle_data_operations()
                elif choice == '7':
                    self.show_system_info()
                elif choice == '8':
                    print("\n💾 Saving data before exit...")
                    self.system.save_data()
                    print("\n👋 Thank you for using School Management System!")
                    print("Goodbye! 🚀")
                    self.running = False
                else:
                    print("❌ Invalid choice! Please enter 1-8.")
                
                if self.running:
                    input("\n↵ Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user. Saving data...")
                self.system.save_data()
                print("👋 Goodbye!")
                break
            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                print(f"\n❌ An unexpected error occurred. Check {Config.LOG_FILE} for details.")
                input("\n↵ Press Enter to continue...")


# ============================================
# 🚀 MAIN EXECUTION
# ============================================
if __name__ == "__main__":
    print("Starting School Management System...")
    # Initialize and run the system
    cli = SchoolCLI()
    cli.run()